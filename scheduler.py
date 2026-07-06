import requests
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from twilio.rest import Client

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
    # Calculamos el disparo exacto 2 horas antes de la clase
    tiempo_disparo = fecha_hora_clase - timedelta(hours=2)
    hora_clase_int = fecha_hora_clase.hour
    fecha_texto = fecha_hora_clase.strftime('%d/%b a las %I:00 %p')
    
    # Regla de seguridad: Si agendan de emergencia a menos de 2 horas, dispara en 1 minuto
    if tiempo_disparo < datetime.now():
        tiempo_disparo = datetime.now() + timedelta(minutes=1)

    reloj.add_job(
        enviar_notificaciones_clase,
        trigger='date',
        run_date=tiempo_disparo,
        args=[telefono_cliente, materia, hora_clase_int, fecha_texto]
    )
    print(f"\n[RELOJ ACTIVADO] 🕒 Tarea en segundo plano programada para: {tiempo_disparo.strftime('%d/%b a las %I:%M:%S %p')}")