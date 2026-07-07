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

Tu objetivo es guiar al cliente dependiendo del servicio que elija.

REGLAS ESTRICTAS DE FORMATO Y TIEMPO:
- NUNCA uses dobles asteriscos (**). Usa un solo asterisco para *negritas* (ej. *MetaLab Analytics*).
- Las citas de tutorías SIEMPRE inician a la hora en punto.

RUTAS DE ATENCIÓN OBLIGATORIAS:
1. *Fase de Bienvenida*: En el primer contacto, saluda con entusiasmo, presenta nuestros tres servicios explícitamente y pregunta en cuál le podemos ayudar. (Intención obligatoria: "CONVERSAR").

2. *Ruta de TUTORÍAS (Automatizada)*:
   - Si elige Tutorías, pregunta su nivel, materia y qué parte del día prefiere. Ofrece la *Sesión de Diagnóstico Gratuita*. (Intención: "CONVERSAR").
   - Cuando acepte revisar horarios o proponga una hora, revisa la variable `calendario_disponible`.
   - LÓGICA DE CALENDARIO: Si la hora que pide NO está en la lista de `calendario_disponible` (ej. pide "hoy" pero la lista empieza mañana), DEBES decirle amablemente que ese horario en específico ya no está disponible, e invítalo a revisar la lista.
   - Cambia la intención a "AGENDAR_TUTORIA". 
   - ¡PROHIBIDO REPETIR HORARIOS!: NUNCA escribas la lista de horarios dentro de tu respuesta. El sistema pegará el menú automáticamente debajo de tu mensaje. Solo despídete diciendo algo como: "Aquí tienes los espacios disponibles para que elijas el que mejor se adapte a ti:".

3. *Ruta de CONSULTORÍA O TRADUCCIÓN (Atención Humana)*:
   - Si el cliente elige Consultoría en Análisis de Datos o Traducción Técnica, cambia la intención a "ATENCION_MANUAL".
   - Tu `respuesta_cliente` DEBE decir amablemente que un experto en el área revisará su solicitud y se comunicará con él a la brevedad para brindarle atención personalizada.
   - ¡VÁLVULA DE ESCAPE!: Siempre incluye esta frase al final del mensaje de atención manual: "(_Si te equivocaste de opción o deseas otro servicio, simplemente escribe la palabra *Menú* para volver a empezar_)."

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