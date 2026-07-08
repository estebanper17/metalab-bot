from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models

def obtener_horarios_disponibles(db: Session, dias_a_futuro: int = 7, preferencia: str = None) -> list:
    # AJUSTE DE ZONA HORARIA: Convertimos la hora UTC del servidor a la hora local (UTC-6)
    hora_utc = datetime.utcnow()
    hoy_completo = hora_utc - timedelta(hours=6)
    hoy_solo_fecha = hoy_completo.date()
    
    slots_disponibles = []
    
    FECHA_CAMBIO_UNI = datetime(2026, 8, 10).date()
    FIN_SEMANA_DESCANSO_BASE = datetime(2026, 7, 18).date()

    # Empezamos en 0 (Hoy)
    for i in range(0, dias_a_futuro):
        fecha_evaluar = hoy_solo_fecha + timedelta(days=i)
        dia_semana = fecha_evaluar.weekday()
        
        # Regla 1: Exclusión de Fines de Semana de Descanso
        dias_diferencia = (fecha_evaluar - FIN_SEMANA_DESCANSO_BASE).days
        if dias_diferencia >= 0 and dia_semana in [5, 6]:
            if (dias_diferencia // 7) % 3 == 0:
                continue

        # Regla 2: Definición de Horarios Base
        if fecha_evaluar >= FECHA_CAMBIO_UNI:
            if dia_semana in [0, 1, 2, 3, 4]: hora_inicio, hora_fin = 16, 20  
            elif dia_semana == 5: hora_inicio, hora_fin = 9, 19
            else: hora_inicio, hora_fin = 10, 15
        else:
            if dia_semana in [0, 1, 2, 3, 4]: hora_inicio, hora_fin = 8, 18
            elif dia_semana == 5: hora_inicio, hora_fin = 9, 19
            else: hora_inicio, hora_fin = 10, 15

        # Regla 3: Validación contra Ocupación Real, El Pasado y Preferencias UX
        for hora in range(hora_inicio, hora_fin):
            dt_slot = datetime.combine(fecha_evaluar, datetime.min.time()).replace(hour=hora)
            
            # FILTRO 1: Si la hora generada ya pasó el día de hoy, la ignoramos
            if dt_slot <= hoy_completo:
                continue

            # 👉 FILTRO UX: Descartar según preferencia de mañana o tarde
            if preferencia == "mañana" and dt_slot.hour >= 14: # Consideramos tarde a partir de las 2 PM (14:00)
                continue
            if preferencia == "tarde" and dt_slot.hour < 14: # Consideramos mañana antes de las 2 PM
                continue
            
            slot_ocupado = db.query(models.CitaTutoria).filter(
                models.CitaTutoria.fecha_hora_inicio == dt_slot,
                models.CitaTutoria.estado == "CONFIRMADA"
            ).first()
            
            if not slot_ocupado:
                slots_disponibles.append(dt_slot)
                
    return slots_disponibles

def formatear_slots_para_whatsapp(slots: list) -> str:
    """Convierte la lista de objetos datetime en un menú legible para el cliente."""
    if not slots:
        return "Lo siento, no tengo horarios disponibles para esa preferencia. Escribe *Menú* para regresar y elegir otra opción."
        
    texto = "🗓️ *Horarios Disponibles para esta semana:*\n"
    texto += "Por favor, responde con el *número* de la opción que prefieras:\n\n"
    
    # Limitamos a mostrar máximo 10 opciones para no saturar la pantalla de WhatsApp
    for indice, slot in enumerate(slots[:10], start=1):
        dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        nombre_dia = dias_es[slot.weekday()]
        fecha_str = slot.strftime('%d/%b')
        hora_12 = slot.strftime('%I:00 %p')
        
        texto += f"*{indice}.* {nombre_dia} {fecha_str} a las {hora_12}\n"
        
    texto += "\n_(Escribe *Menú* en cualquier momento para cancelar)_"
    return texto