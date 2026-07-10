import os
import requests
from datetime import datetime, timedelta
from fastapi import FastAPI, Form, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from twilio.twiml.messaging_response import MessagingResponse

from database import engine, get_db
import models
from calendar_engine import obtener_horarios_disponibles, formatear_slots_para_whatsapp
from scheduler import programar_recordatorios_clase
from gemini_service import analizar_mensaje_con_gemini
from dotenv import load_dotenv 
from sqlalchemy.orm.attributes import flag_modified

load_dotenv() 

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MetaLab Analytics - Versión Final Inteligente")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_alerta_telegram(mensaje: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload)
    except Exception as e: print(f"❌ Error Telegram: {e}")

# =========================================================================
# RUTA DE "LATIDO" PARA MANTENER EL SERVIDOR DESPIERTO EN RENDER
# =========================================================================
@app.get("/ping")
async def keep_alive():
    return {"status": "ok", "mensaje": "MetaLab Analytics Bot está despierto y operando"}

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
        # 1. Recuperamos los datos temporales y extraemos la preferencia de horario si ya existe
        datos = dict(cliente.datos_temporales)
        preferencia_actual = datos.get("preferencia_horario")
        
        # 2. TRAER LOS HORARIOS REALES (Filtrados por preferencia si la hay)
        slots_disponibles = obtener_horarios_disponibles(db, dias_a_futuro=7, preferencia=preferencia_actual)
        
        # 👉 SÚPER VISIÓN: Le pasamos hasta 30 opciones a Gemini para que tenga contexto de varios días
        horarios_legibles = [slot.strftime('%d/%b a las %I:00 %p') for slot in slots_disponibles[:30]]
        
        datos["calendario_disponible"] = horarios_legibles 
        
        # Darle a Gemini la fecha actual de México para que no se pierda
        hora_local_mexico = datetime.utcnow() - timedelta(hours=6)
        datos["fecha_actual_sistema"] = f"INFORMACIÓN DEL SISTEMA: Hoy es {hora_local_mexico.strftime('%d/%b')}"
        
        # 3. Ahora sí, llamamos a Gemini con los ojos abiertos
        analisis = analizar_mensaje_con_gemini(text_limpio, datos)
        
        intencion = analisis.get("intencion_detectada", "CONVERSAR")
        respuesta_bot = analisis.get("respuesta_cliente", "")
        
        # 4. Actualizamos las variables detectadas por el JSON
        if analisis.get("materia"): datos["materia"] = analisis.get("materia")
        if analisis.get("nivel"): datos["nivel"] = analisis.get("nivel")
        if analisis.get("preferencia_horario"): datos["preferencia_horario"] = analisis.get("preferencia_horario")
        
        # Inicializamos el arreglo de historial si es un cliente nuevo
        if "historial" not in datos:
            datos["historial"] = []
            
        # Almacenamos el ida y vuelta en la memoria del bot
        datos["historial"].append({"autor": "Usuario", "texto": text_limpio})
        datos["historial"].append({"autor": "Asistente", "texto": respuesta_bot})
        
        # Mantenemos solo los últimos 10 mensajes para optimizar espacio
        datos["historial"] = datos["historial"][-10:]
        
        cliente.datos_temporales = datos
        flag_modified(cliente, "datos_temporales")  # Nos aseguramos de guardar la memoria y el nuevo contexto
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
            
            # Blindaje: Si Gemini no generó respuesta, usamos esta por defecto
            mensaje_manual = respuesta_bot if respuesta_bot.strip() else "¡Excelente! Un experto en el área revisará tu solicitud y se pondrá en contacto contigo por este medio a la brevedad.\n\n_(Si te equivocaste de opción o deseas otro servicio, simplemente escribe la palabra *Menú* para volver a empezar)._"
            
            twiml.message(mensaje_manual)
            print(f"\n[DEBUG GEMINI - ATENCIÓN MANUAL]:\n{mensaje_manual}") 
            
            # ALERTA INMEDIATA DE OTROS SERVICIOS
            enviar_alerta_telegram(
                f"🚨 *ALERTA DE ATENCIÓN MANUAL* 🚨\n\n"
                f"👤 *Contacto:* `{From}`\n"
                f"💬 *Mensaje del usuario:* {text_limpio}\n\n"
                f"👉 _Entrar al chat de inmediato para dar seguimiento personalizado._"
            )
            return Response(content=str(twiml), media_type="application/xml")
            
        elif intencion == "AGENDAR_TUTORIA":
            preferencia_actual = cliente.datos_temporales.get("preferencia_horario")
            slots = obtener_horarios_disponibles(db, dias_a_futuro=7, preferencia=preferencia_actual)
            
            # 👉 UX CLIENTE: Guardamos solo los primeros 10 espacios filtrados para presentarlos en WhatsApp
            datos["slots_ofrecidos"] = [slot.isoformat() for slot in slots[:10]]
            cliente.datos_temporales = datos
            cliente.estado_actual = "TUTORIAS_HORARIO"
            db.commit()
            
            introduccion = f"{respuesta_bot}\n\n"
            menu_horarios = formatear_slots_para_whatsapp(slots[:10])
            
            twiml.message(introduccion + menu_horarios)
            
            print(f"\n[DEBUG INTEGRACIÓN GEMINI - TRANSFERENCIA A CALENDARIO]:\n{introduccion}{menu_horarios}")
            print(f"\n[DEBUG CALENDARIO DETALLADO]")
            print(f"Hora Servidor (UTC): {datetime.utcnow()}")
            print(f"Hora Local (Ajustada): {datetime.utcnow() - timedelta(hours=6)}")
            print(f"Slots generados (Total): {[s.strftime('%H:%M') for s in slots]}")
            print(f"Texto menú mostrado al cliente (Max 10): {horarios_legibles[:10]}")
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

            print(f"\n[DEBUG - CONFIRMACIÓN AL CLIENTE (BLOQUEADA POR TWILIO)]:\n{respuesta}")
            
            programar_recordatorios_clase(From, nueva_cita.materia, fecha_hora_dt)
            
        else:
            # VÁLVULA DE ESCAPE: El usuario respondió con texto en lugar de un número
            horarios_legibles = [datetime.fromisoformat(s).strftime('%d/%b a las %I:00 %p') for s in slots_ofrecidos]
            datos["contexto_calendario"] = f"NOTA DEL SISTEMA: El calendario real solo tiene estos espacios filtrados para el usuario: {horarios_legibles}. Explícale esto de forma amable."
            
            analisis = analizar_mensaje_con_gemini(text_limpio, datos)
            respuesta_bot = analisis.get("respuesta_cliente", "")
            
            if "historial" not in datos: datos["historial"] = []
            datos["historial"].append({"autor": "Usuario", "texto": text_limpio})
            datos["historial"].append({"autor": "Asistente", "texto": respuesta_bot})
            datos["historial"] = datos["historial"][-10:]
            
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