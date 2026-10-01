"""Cliente del modelo de lenguaje (Google Gemini) para el asistente de RespiraKids.

El modelo NO responde con su conocimiento general: solo redacta a partir de los fragmentos del
documento maestro que le entrega `app/asistente/servicio.py`, y debe citarlos. Si falla o no está
configurado, devuelve None y el servicio responde de forma extractiva.
"""
from flask import current_app
from google import genai
from google.genai import types

INSTRUCCIONES_SISTEMA = """Eres el asistente de información de RespiraKids, una aplicación para cuidadores de niños y niñas menores de 5 años.

REGLAS OBLIGATORIAS:
1. Responde ÚNICAMENTE con la información de los FRAGMENTOS que se te entregan. No uses ningún otro conocimiento.
2. Cita cada afirmación con el número del fragmento entre corchetes, por ejemplo [1] o [2], e indica de qué condición proviene (aparece en el título del fragmento). No generalices a otras condiciones lo que la fuente dice para una.
3. Si los fragmentos no responden la pregunta, contesta exactamente: "NO DISPONIBLE EN LA FUENTE CONSULTADA" y sugiere consultar a un profesional de salud.
4. NUNCA diagnostiques ni digas qué enfermedad tiene el niño o niña. Puedes decir que algo "coincide con lo que la fuente describe".
5. NUNCA recomiendes medicamentos ni dosis, aunque aparezcan en los fragmentos.
6. NUNCA cambies ni contradigas la clasificación de riesgo que dio la aplicación (verde, amarillo o rojo).
7. Si la pregunta menciona signos de alarma, indica buscar atención en un servicio de salud de inmediato.
8. No te presentes como médico. Usa español claro y sencillo, en 3 a 6 líneas. Usa "- " para listas."""


def _fragmentos_como_texto(fragmentos):
    return '\n\n'.join(f'[{i}] {f.titulo}\n{f.contenido}' for i, f in enumerate(fragmentos, start=1))


def generar_respuesta_fundamentada(pregunta, fragmentos, contexto=None, historial=None):
    """Texto generado a partir de los fragmentos, o None si el modelo no está disponible o falla."""
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key:
        return None

    mensaje = f'FRAGMENTOS DE LA FUENTE:\n{_fragmentos_como_texto(fragmentos)}\n\n'
    if contexto:
        mensaje += (f'CONTEXTO: el cuidador pregunta sobre una evaluación de RespiraKids con nivel '
                    f'"{contexto.get("nivel")}" y estas señales: {", ".join(contexto.get("senales", [])) or "ninguna"}. '
                    'No modifiques esa clasificación.\n\n')
    mensaje += f'PREGUNTA: {pregunta}'

    contenidos = [
        types.Content(role='user' if m.get('role') == 'user' else 'model', parts=[types.Part(text=m.get('content', ''))])
        for m in (historial or [])
    ]
    contenidos.append(types.Content(role='user', parts=[types.Part(text=mensaje)]))

    try:
        client = genai.Client(api_key=api_key)
        respuesta = client.models.generate_content(
            model=current_app.config['GEMINI_MODEL'],
            contents=contenidos,
            config=types.GenerateContentConfig(system_instruction=INSTRUCCIONES_SISTEMA, temperature=0.1),
        )
        return (respuesta.text or '').strip() or None
    except Exception:
        current_app.logger.exception('Error al consultar el modelo del asistente')
        return None
