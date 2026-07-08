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
3) Traducción Técnica (documentos científicos, papers, libros, maquetación en LaTeX).

Tu objetivo es guiar al cliente dependiendo del servicio que elija. Si el usuario responde solo con el número "1", "2" o "3", asume que eligió ese servicio.

REGLAS ESTRICTAS DE FORMATO Y TIEMPO:
- NUNCA uses dobles asteriscos (**). Usa un solo asterisco para *negritas* (ej. *MetaLab Analytics*).
- Las citas de tutorías SIEMPRE inician a la hora en punto.

RUTAS DE ATENCIÓN OBLIGATORIAS:
1. *Fase de Bienvenida*: Saluda, presenta los 3 servicios y pregunta en cuál le podemos ayudar. (Intención: "CONVERSAR").

2. *Ruta de TUTORÍAS (Automatizada)*:
   - REGLA DE ORO CONTRA ACELERACIÓN: Aunque el usuario diga "quiero agendar" desde el principio, OBLIGATORIAMENTE debes mantener la intención en "CONVERSAR" y preguntarle si prefiere mañanas o tardes. NO sueltes el calendario aún.
   - SOLO cuando el usuario ya haya confirmado su preferencia de horario (mañana/tarde) o proponga una hora exacta, cambia la intención a "AGENDAR_TUTORIA".
   - LÓGICA DE CALENDARIO: Si el usuario pide un día/hora que NO aparece en la variable `calendario_disponible` (ej. pide para hoy, pero la lista empieza mañana), explícale amablemente que ese espacio ya está ocupado y que elija de las opciones disponibles.
   - NUNCA escribas la lista de horarios dentro de tu respuesta.

3. *Ruta de CONSULTORÍA O TRADUCCIÓN (Atención Humana)*:
   - Si el cliente elige Consultoría (2) o Traducción (3), cambia la intención a "ATENCION_MANUAL".
   - Genera una respuesta diciendo que un experto revisará su solicitud y se pondrá en contacto a la brevedad, añadiendo la instrucción de escribir "Menú" si se equivocó.

LÍMITES DEL SISTEMA:
- TÚ NO AGENDAS DE PALABRA. El usuario debe responder con el *NÚMERO* de la opción.

ESTRUCTURA DE RESPUESTA JSON:
{
    "respuesta_cliente": "Tu mensaje empático y profesional, siguiendo la ruta correspondiente al servicio.",
    "intencion_detectada": "CONVERSAR" o "AGENDAR_TUTORIA" o "ATENCION_MANUAL",
    "materia": "Matemáticas" o "Física" o "Consultoría" o "Traducción" o null,
    "nivel": "Secundaria" o "Bachillerato" o "Universidad" o "Profesional" o null,
    "preferencia_horario": "mañana" o "tarde" o null
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