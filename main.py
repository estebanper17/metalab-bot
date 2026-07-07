import os
import requests
from datetime import datetime
from fastapi import FastAPI, Form, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from twilio.twiml.messaging_response import MessagingResponse

from database import engine, get_db
import models
from calendar_engine import obtener_horarios_disponibles, formatear_slots_para_whatsapp
from scheduler import programar_recordatorios_clase
from gemini_service import analizar_mensaje_con_gemini
from dotenv import load_dotenv # <--- Asegúrate de tener este import
from sqlalchemy.orm.attributes import flag_modified

load_dotenv() # Esto carga las variables del archivo .env

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MetaLab Analytics - Versión Final Inteligente")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_alerta_telegram(mensaje: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except Exception as e: print(f"❌ Error Telegram: {e}")

@app.post("/webhook")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...), db: Session = Depends(get_db)):
    text_limpio = Body.strip()
    text_minusculas = text_limpio.lower()
    twiml = MessagingResponse()

    cliente = db.query(models.ClienteEstado).filter(models.ClienteEstado.telefono == From).first()
    if not cliente:
        cliente = models.ClienteEstado(telefono=From, estado_actual="INICIO", datos_temporales={})
        db.add(cliente)
        db.commit()
        db.refresh(cliente)

    # BOTÓN DE PÁNICO GLOBAL
    if text_minusculas in ["menu", "menú", "volver", "inicio", "cancelar"]:
        cliente.estado_actual = "INICIO"
        cliente.datos_temporales = {}
        db.commit()

    estado_actual = cliente.estado_actual
    print(f"\n[MENSAJE RECIBIDO] De: {From} | Estado: {estado_actual} | Texto: {text_limpio}")
    
    # =========================================================================
    # FASE CONVERSACIONAL INTEGRADA CON GEMINI (INICIO / ESPERANDO_SERVICIO)
    # =========================================================================
    if estado_actual in ["INICIO", "ESPERANDO_SERVICIO"]:
        analisis = analizar_mensaje_con_gemini(text_limpio, cliente.datos_temporales)
        
        intencion = analisis.get("intencion_detectada", "CONVERSAR")
        respuesta_bot = analisis.get("respuesta_cliente", "")
        
        # 1. Recuperamos y actualizamos las variables y el historial en el JSON
        datos = dict(cliente.datos_temporales)
        if analisis.get("materia"): datos["materia"] = analisis.get("materia")
        if analisis.get("nivel"): datos["nivel"] = analisis.get("nivel")
        
        # Inicializamos el arreglo de historial si es un cliente nuevo
        if "historial" not in datos:
            datos["historial"] = []
            
        # Almacenamos el ida y vuelta en la memoria del bot
        datos["historial"].append({"autor": "Usuario", "texto": text_limpio})
        datos["historial"].append({"autor": "Asistente", "texto": respuesta_bot})
        
        # Mantenemos solo los últimos 10 mensajes para optimizar espacio
        datos["historial"] = datos["historial"][-10:]
        
        cliente.datos_temporales = datos
        flag_modified(cliente, "datos_temporales")
        db.commit()

        if intencion == "CONVERSAR":
            cliente.estado_actual = "ESPERANDO_SERVICIO"
            db.commit()
            twiml.message(respuesta_bot)
            
            print(f"\n[DEBUG GEMINI - MODO CONVERSACIÓN]:\n{respuesta_bot}")
            return Response(content=str(twiml), media_type="application/xml")
            
        elif intencion == "ATENCION_MANUAL":
            cliente.estado_actual = "ATENCION_MANUAL"
            db.commit()
            twiml.message(respuesta_bot)
            
            # ALERTA INMEDIATA DE OTROS SERVICIOS
            enviar_alerta_telegram(
                f"🚨 *ALERTA DE ATENCIÓN MANUAL* 🚨\n\n"
                f"👤 *Contacto:* `{From}`\n"
                f"💬 *Mensaje del usuario:* {text_limpio}\n\n"
                f"👉 _Entrar al chat de inmediato para dar seguimiento personalizado._"
            )
            return Response(content=str(twiml), media_type="application/xml")
            
        elif intencion == "AGENDAR_TUTORIA":
            slots = obtener_horarios_disponibles(db, dias_a_futuro=7)
            datos["slots_ofrecidos"] = [slot.isoformat() for slot in slots[:8]]
            cliente.datos_temporales = datos
            cliente.estado_actual = "TUTORIAS_HORARIO"
            db.commit()
            
            introduccion = f"{respuesta_bot}\n\n"
            menu_horarios = formatear_slots_para_whatsapp(slots)
            
            twiml.message(introduccion + menu_horarios)
            
            # CORRECCIÓN AQUÍ: Imprime el texto completo para validar el contexto
            print(f"\n[DEBUG INTEGRACIÓN GEMINI - TRANSFERENCIA A CALENDARIO]:\n{introduccion}{menu_horarios}")
            return Response(content=str(twiml), media_type="application/xml")

    # =========================================================================
    # ESTADO 5: TUTORIAS - GUARDAR CITA EN BD (CON ALERTA INMEDIATA)
    # =========================================================================
    elif estado_actual == "TUTORIAS_HORARIO":
        datos = dict(cliente.datos_temporales)
        slots_ofrecidos = datos.get("slots_ofrecidos", [])
        
        if text_limpio.isdigit() and 1 <= int(text_limpio) <= len(slots_ofrecidos):
            opcion_elegida = int(text_limpio) - 1
            fecha_hora_dt = datetime.fromisoformat(slots_ofrecidos[opcion_elegida])
            
            nueva_cita = models.CitaTutoria(
                telefono_cliente=From,
                materia=datos.get("materia"),
                nivel=datos.get("nivel"),
                fecha_hora_inicio=fecha_hora_dt,
                estado="CONFIRMADA"
            )
            db.add(nueva_cita)
            
            cliente.estado_actual = "INICIO"
            cliente.datos_temporales = {}
            db.commit()
            
            fecha_str = fecha_hora_dt.strftime('%d/%b a las %I:00 %p')
            
            # ALERTA INMEDIATA DE CLASE AGENDADA
            alerta_inmediata = (
                f"✅ *NUEVA SESIÓN REGISTRADA EN EL BOT* ✅\n\n"
                f"📚 *Materia:* {nueva_cita.materia} ({nueva_cita.nivel})\n"
                f"🗓️ *Fecha y Hora:* {fecha_str}\n"
                f"👤 *Contacto Alumno:* `{From}`\n\n"
                f"👉 _El reloj del sistema ha programado la segunda alerta con los links de Google Meet para 2 horas antes de iniciar._"
            )
            enviar_alerta_telegram(alerta_inmediata)
            
            # Confirmación al cliente
            respuesta = (
                f"🎉 *¡Sesión agendada con éxito en nuestro sistema!* 🎉\n\n"
                f"• *Materia:* {nueva_cita.materia}\n"
                f"• *Nivel:* {nueva_cita.nivel}\n"
                f"• *Horario:* {fecha_str}\n\n"
                "Recibirás un recordatorio automático 2 horas antes de iniciar con tu link de acceso a Google Meet. ¡Nos vemos en MetaLab Analytics!"
            )
            twiml.message(respuesta)

            # ---> AGREGA ESTA LÍNEA PARA VERLO EN CONSOLA <---
            print(f"\n[DEBUG - CONFIRMACIÓN AL CLIENTE (BLOQUEADA POR TWILIO)]:\n{respuesta}")
            
            programar_recordatorios_clase(From, nueva_cita.materia, fecha_hora_dt)
            
        else:
            # VÁLVULA DE ESCAPE: El usuario respondió con texto en lugar de un número
            
            # 1. Le decimos a Gemini la verdad sobre los horarios para que no alucine
            horarios_legibles = [datetime.fromisoformat(s).strftime('%d/%b a las %I:00 %p') for s in slots_ofrecidos]
            datos["contexto_calendario"] = f"NOTA DEL SISTEMA: El calendario real solo tiene estos espacios: {horarios_legibles}. Explícale esto al usuario de forma amable."
            
            analisis = analizar_mensaje_con_gemini(text_limpio, datos)
            respuesta_bot = analisis.get("respuesta_cliente", "")
            
            # 2. Guardamos la memoria
            if "historial" not in datos: datos["historial"] = []
            datos["historial"].append({"autor": "Usuario", "texto": text_limpio})
            datos["historial"].append({"autor": "Asistente", "texto": respuesta_bot})
            datos["historial"] = datos["historial"][-10:]
            
            # 3. ¡LA LLAVE DE SALIDA! Regresamos a modo conversacional
            cliente.estado_actual = "ESPERANDO_SERVICIO"
            cliente.datos_temporales = datos
            flag_modified(cliente, "datos_temporales")
            db.commit()
            
            twiml.message(respuesta_bot)
            print(f"\n[DEBUG GEMINI - VÁLVULA DE ESCAPE]:\n{respuesta_bot}")
            
            return Response(content=str(twiml), media_type="application/xml")


    elif estado_actual == "ATENCION_MANUAL":
        return Response(status_code=200)

    return Response(content=str(twiml), media_type="application/xml")