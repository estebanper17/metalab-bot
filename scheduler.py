import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv # <--- Asegúrate de tener este import
from apscheduler.schedulers.background import BackgroundScheduler
from twilio.rest import Client

# Cargamos la bóveda por si ejecutamos este archivo por separado
load_dotenv() 

# --- CREDENCIALES ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
    
    # 1. RECORDATORIO AL ALUMNO (VÍA WHATSAPP)
    try:
        cliente_twilio = Client(TWILIO_SID, TWILIO_TOKEN)
        mensaje_wa = (
            f"⏳ *Recordatorio de MetaLab Analytics* ⏳\n\n"
            f"Tu sesión de *{materia}* comienza en *2 horas*.\n\n"
            f"🔗 *Enlace de acceso a Google Meet:*\n{link_meet}\n\n"
            f"¡Te vemos en un momento!"
        )
        cliente_twilio.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=mensaje_wa,
            to=telefono_cliente
        )
        print(f"✅ Recordatorio enviado a WhatsApp del alumno: {telefono_cliente}")
    except Exception as e:
        print(f"❌ Error enviando WhatsApp de recordatorio: {e}")

    # 2. RECORDATORIO PARA TI (VÍA TELEGRAM)
    try:
        url_telegram = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        alerta_admin = (
            f"⏳ *RECORDATORIO: CLASE EN 2 HORAS* ⏳\n\n"
            f"📚 *Materia:* {materia}\n"
            f"👤 *Alumno:* `{telefono_cliente}`\n"
            f"🔗 *Tu Link de Acceso:* {link_meet}"
        )
        requests.post(url_telegram, json={"chat_id": TELEGRAM_CHAT_ID, "text": alerta_admin, "parse_mode": "Markdown"})
        print("✅ Recordatorio interno enviado a Telegram")
    except Exception as e:
        print(f"❌ Error enviando recordatorio a Telegram: {e}")

# Inicializamos el reloj en segundo plano
reloj = BackgroundScheduler()
reloj.start()

def programar_recordatorios_clase(telefono_cliente: str, materia: str, fecha_hora_clase: datetime):
    # 1. Calculamos la hora de disparo en hora local (Puebla)
    tiempo_disparo_local = fecha_hora_clase - timedelta(hours=2)
    hora_clase_int = fecha_hora_clase.hour
    fecha_texto = fecha_hora_clase.strftime('%d/%b a las %I:00 %p')
    
    # 2. Obtenemos la hora actual real en México (UTC-6)
    hora_actual_local = datetime.utcnow() - timedelta(hours=6)
    
    # Regla de seguridad: Si agendan de emergencia a menos de 2 horas, dispara en 1 minuto
    if tiempo_disparo_local < hora_actual_local:
        tiempo_disparo_local = hora_actual_local + timedelta(minutes=1)

    # 3. TRADUCCIÓN AL SERVIDOR: Como APScheduler lee el reloj interno de Render (UTC),
    # le sumamos 6 horas al tiempo de disparo para que el servidor lo detone en el momento correcto.
    tiempo_disparo_servidor = tiempo_disparo_local + timedelta(hours=6)

    reloj.add_job(
        enviar_notificaciones_clase,
        trigger='date',
        run_date=tiempo_disparo_servidor,
        args=[telefono_cliente, materia, hora_clase_int, fecha_texto]
    )
    print(f"\n[RELOJ ACTIVADO] 🕒 Tarea programada en el servidor. El cliente la recibirá a las: {tiempo_disparo_local.strftime('%d/%b a las %I:%M:%S %p')} (Hora local)")