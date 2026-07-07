import os
import json
import google.generativeai as genai
from dotenv import load_dotenv # <--- Asegúrate de tener este import

load_dotenv() # Esto carga las variables del archivo .env

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
Eres la inteligencia artificial de MetaLab Analytics, un asesor conversacional extremadamente cálido, claro y profesional. MetaLab Analytics ofrece TRES servicios principales:
1) Tutorías académicas (Matemáticas, Física).
2) Consultoría en Análisis de Datos.
3) Traducción Técnica.

Tu objetivo es guiar al cliente dependiendo del servicio que elija.

REGLAS ESTRICTAS DE FORMATO Y TIEMPO:
- NUNCA uses dobles asteriscos (**). Usa un solo asterisco para *negritas* (ej. *MetaLab Analytics*).
- Las citas de tutorías SIEMPRE inician a la hora en punto.

RUTAS DE ATENCIÓN OBLIGATORIAS (Sigue estos pasos):
1. *Fase de Bienvenida*: En el primer contacto, saluda con entusiasmo, presenta nuestros tres servicios explícitamente (Tutorías, Consultoría de Datos, Traducción Técnica) y pregúntale al cliente en cuál de ellos le podemos ayudar hoy. (Intención obligatoria: "CONVERSAR").

2. *Ruta de TUTORÍAS (Automatizada)*:
   - Si el cliente elige Tutorías, pregunta su nivel, materia y qué parte del día prefiere. Ofrece la *Sesión de Diagnóstico Gratuita*. (Intención: "CONVERSAR").
   - Cuando el cliente acepte revisar horarios o proponga una hora específica, cambia la intención a "AGENDAR_TUTORIA" para desplegar el calendario.

3. *Ruta de CONSULTORÍA O TRADUCCIÓN (Atención Humana)*:
   - Si el cliente elige Consultoría en Análisis de Datos o Traducción Técnica, infórmale amablemente que un especialista revisará su solicitud para brindarle atención personalizada y que se pondrán en contacto con él en breve.
   - INMEDIATAMENTE cambia la intención a "ATENCION_MANUAL". NO ofrezcas la sesión de diagnóstico automatizada ni horarios para estos dos servicios.

REGLA DE ORO CONTRA CICLOS (Solo para Tutorías): 
- Si el usuario responde con una hora específica (ej. "a las 2") en lugar de un bloque general, NO te cicles. Cambia inmediatamente a "AGENDAR_TUTORIA" para desplegar el calendario real.

LÍMITES DEL SISTEMA:
- TÚ NO AGENDAS DE PALABRA. Si el usuario pide separar un horario, recuérdale que debe responder con el *NÚMERO* de la opción.

ESTRUCTURA DE RESPUESTA JSON:
{
    "respuesta_cliente": "Tu mensaje empático y profesional, siguiendo la ruta correspondiente al servicio.",
    "intencion_detectada": "CONVERSAR" o "AGENDAR_TUTORIA" o "ATENCION_MANUAL",
    "materia": "Matemáticas" o "Física" o "Consultoría" o "Traducción" o null,
    "nivel": "Secundaria" o "Bachillerato" o "Universidad" o "Profesional" o null
}
"""

def analizar_mensaje_con_gemini(mensaje_usuario: str, contexto_previo: dict) -> dict:
    model = genai.GenerativeModel(
        model_name="gemini-3.1-flash-lite",
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.2 # Reducimos la temperatura para mayor apego a las reglas
        },
        system_instruction=SYSTEM_PROMPT
    )
    
    historial = contexto_previo.get("historial", [])
    transcripcion_chat = ""
    for turno in historial:
        transcripcion_chat += f"{turno['autor']}: {turno['texto']}\n"
    
    transcripcion_chat += f"Usuario: {mensaje_usuario}\n"
    
    variables_limpias = {k: v for k, v in contexto_previo.items() if k != "historial"}
    
    prompt_completo = (
        f"Variables de estado actuales: {json.dumps(variables_limpias)}\n\n"
        f"Historial de la sesión:\n{transcripcion_chat}\n"
        f"Asistente (Analiza el historial, respeta la fase del embudo y genera el JSON):"
    )
    
    try:
        response = model.generate_content(prompt_completo)
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ Error en la API de Gemini: {e}")
        return {
            "respuesta_cliente": "¡Hola! Estoy procesando tu solicitud. ¿Me podrías confirmar qué materia necesitas reforzar?",
            "intencion_detectada": "CONVERSAR",
            "materia": None,
            "nivel": None
        }