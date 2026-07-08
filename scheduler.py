import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv 
from apscheduler.schedulers.background import BackgroundScheduler
from twilio.rest import Client

load_dotenv() 

# --- CREDENCIALES ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"

MEET_LINKS = {
    8: "https://meet.google.com/hdj-vwwk-vot",
    9: "https://meet.google.com/urc-sjjk-soa",
    10: "https://meet.google.com/fks-grsv-oqe",
    11: "https://meet.google.com/vof-mjks-ggt",
    12: "https://meet.google.com/dfo-abaq-emw",
    13: "https://meet.google.com/rnd-ancj-xks",
    14: "https://meet.google.com/fks-grsv-oqe",
    15: "https://meet.google.com/vof-mjks-ggt",
    16: "https://meet.google.com/qbw-udnr-cdz",
    17: "https://meet.google.com/tzb-rshv-cpt",
    18: "https://meet.google.com/zbp-jppw-hzr"
}

def enviar_notificaciones_clase(telefono_cliente: str, materia: str, hora_clase_int: int, fecha_texto: str):
    """Ejecuta el envío dual 2 horas antes de la sesión"""
    link_meet = MEET_LINKS.get(hora_clase_int, "https://meet.google.com/")
    hora_exacta = fecha_texto.split(" a las ")[-1] # Extraemos solo la hora (ej. "02:00 PM")
    
    # 1. RECORDATORIO AL ALUMNO (VÍA WHATSAPP)
    try:
        cliente_twilio = Client(TWILIO_SID, TWILIO_TOKEN)
        mensaje_wa = (
            f"⏳ *Recordatorio de MetaLab Analytics* ⏳\n\n"
            f"Tu sesión de *{materia}* está programada para hoy a las *{hora_exacta}* (en aproximadamente 2 horas).\n\n"
            f"🔗 *Enlace de acceso a Google Meet:*\n{link_meet}\n\n"
            f"¡Te vemos en un momento!"
        )
        cliente_twilio.messages.create(from_=TWILIO_WHATSAPP_NUMBER, body=mensaje_wa, to=telefono_cliente)
        print(f"\n[DEBUG SCHEDULER - WHATSAPP ENVIADO AL ALUMNO]:\n{mensaje_wa}")
    except Exception as e:
        print(f"❌ Error enviando WhatsApp de recordatorio: {e}")

    # 2. RECORDATORIO PARA TI (VÍA TELEGRAM - 2 HORAS)
    try:
        url_telegram = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        alerta_admin = (
            f"⏳ *RECORDATORIO: CLASE EN 2 HORAS* ⏳\n\n"
            f"📚 *Materia:* {materia}\n"
            f"🗓️ *Horario Exacto:* {fecha_texto}\n"
            f"👤 *Alumno:* `{telefono_cliente}`\n"
            f"🔗 *Tu Link de Acceso:* {link_meet}"
        )
        requests.post(url_telegram, json={"chat_id": TELEGRAM_CHAT_ID, "text": alerta_admin, "parse_mode": "Markdown"})
        print(f"\n[DEBUG SCHEDULER - TELEGRAM ENVIADO A ADMIN (2 HORAS)]:\n{alerta_admin}")
    except Exception as e:
        print(f"❌ Error enviando recordatorio a Telegram: {e}")

def enviar_alerta_10_min_telegram(materia: str, telefono_cliente: str, hora_clase_int: int, fecha_texto: str):
    """Ejecuta una alerta exclusiva para el administrador 10 minutos antes de la clase"""
    link_meet = MEET_LINKS.get(hora_clase_int, "https://meet.google.com/")
    try:
        url_telegram = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        alerta_10m = (
            f"🚨 *¡LA CLASE EMPIEZA EN 10 MINUTOS!* 🚨\n\n"
            f"📚 *Materia:* {materia}\n"
            f"🗓️ *Horario:* {fecha_texto}\n"
            f"👤 *Alumno:* `{telefono_cliente}`\n"
            f"🔗 *Entra aquí ahora:* {link_meet}"
        )
        requests.post(url_telegram, json={"chat_id": TELEGRAM_CHAT_ID, "text": alerta_10m, "parse_mode": "Markdown"})
        print(f"\n[DEBUG SCHEDULER - TELEGRAM ENVIADO A ADMIN (10 MINUTOS)]:\n{alerta_10m}")
    except Exception as e:
        print(f"❌ Error enviando Telegram 10 min: {e}")

# Inicializamos el reloj en segundo plano
reloj = BackgroundScheduler()
reloj.start()

def programar_recordatorios_clase(telefono_cliente: str, materia: str, fecha_hora_clase: datetime):
    # Tiempos en hora local
    tiempo_disparo_2h_local = fecha_hora_clase - timedelta(hours=2)
    tiempo_disparo_10m_local = fecha_hora_clase - timedelta(minutes=10)
    hora_clase_int = fecha_hora_clase.hour
    fecha_texto = fecha_hora_clase.strftime('%d/%b a las %I:00 %p')
    
    hora_actual_local = datetime.utcnow() - timedelta(hours=6)
    
    # Reglas de seguridad si agendan de emergencia
    if tiempo_disparo_2h_local < hora_actual_local:
        tiempo_disparo_2h_local = hora_actual_local + timedelta(minutes=1)
        
    if tiempo_disparo_10m_local < hora_actual_local:
        tiempo_disparo_10m_local = hora_actual_local + timedelta(minutes=2)

    # TRADUCCIÓN AL SERVIDOR (UTC)
    tiempo_disparo_2h_servidor = tiempo_disparo_2h_local + timedelta(hours=6)
    tiempo_disparo_10m_servidor = tiempo_disparo_10m_local + timedelta(hours=6)

    # Programar Trabajo 1: Alerta 2 horas
    reloj.add_job(
        enviar_notificaciones_clase,
        trigger='date',
        run_date=tiempo_disparo_2h_servidor,
        args=[telefono_cliente, materia, hora_clase_int, fecha_texto]
    )
    
    # Programar Trabajo 2: Alerta 10 minutos (Solo Telegram)
    reloj.add_job(
        enviar_alerta_10_min_telegram,
        trigger='date',
        run_date=tiempo_disparo_10m_servidor,
        args=[materia, telefono_cliente, hora_clase_int, fecha_texto]
    )
    
    print(f"\n[RELOJ ACTIVADO] 🕒 Tareas programadas:\n - Alerta de 2 hrs a las: {tiempo_disparo_2h_local.strftime('%I:%M %p')}\n - Alerta de 10 min a las: {tiempo_disparo_10m_local.strftime('%I:%M %p')}")