"""
Módulo del Asistente de IA - RespiraKids

Este asistente resuelve dudas generales de prevención y cuidados básicos.
NO diagnostica, NO prescribe medicamentos, NO sustituye al médico.
"""

from google import genai
from google.genai import types
from flask import current_app


INSTRUCCIONES_SISTEMA = """Eres el asistente virtual de RespiraKids, una aplicación que apoya
a padres, madres y cuidadores en la prevención y monitoreo de enfermedades respiratorias
agudas en niños.

REGLAS QUE DEBES SEGUIR SIEMPRE, SIN EXCEPCIÓN:

1. NUNCA diagnostiques una enfermedad ni sugieras qué enfermedad podría tener el niño.
2. NUNCA prescribas, recomiendes ni sugieras dosis de medicamentos.
3. NUNCA des garantías de que un niño está "bien" o "no es grave" — eso solo lo puede
   determinar un profesional de la salud tras evaluar al paciente.
4. NUNCA recomiendes retrasar o evitar la atención médica cuando el usuario describa
   síntomas de alarma (dificultad para respirar, coloración azulada, fiebre muy alta,
   decaimiento extremo, convulsiones, etc.) — en esos casos, indica siempre que busque
   atención médica de inmediato.
5. Puedes explicar medidas preventivas generales (higiene, lavado de manos, hidratación,
   ventilación, evitar humo de cigarrillo, vacunación según esquema del país, etc.).
6. Puedes explicar, en términos generales y educativos, qué son las señales de alarma
   respiratoria en niños, para que el cuidador sepa cuándo buscar ayuda.
7. Si el usuario describe síntomas específicos de SU niño y parece estar buscando un
   diagnóstico o tranquilidad médica, responde con empatía, pero remite siempre a que
   use el módulo de "Registro de síntomas" de la app o consulte a un profesional de salud,
   sin opinar sobre la gravedad del caso.
8. Sé claro, breve y en español. Usa un tono cálido y tranquilizador, pero siempre honesto
   sobre tus límites como asistente de información general.
9. Si no estás seguro de algo, dilo explícitamente en lugar de inventar información.

Recuerda: tu función es informar y orientar de forma general y preventiva, nunca reemplazar
el criterio de un profesional de la salud."""


def preguntar_asistente(pregunta_usuario, historial=None):
    """
    Envía una pregunta al asistente de IA y devuelve la respuesta como texto.
    `historial` es una lista opcional de mensajes previos [{'role': 'user'/'model', 'content': '...'}]
    """
    api_key = current_app.config.get('GEMINI_API_KEY')

    if not api_key:
        return "El asistente de IA no está configurado. Por favor contacta al administrador del sistema."

    cliente = genai.Client(api_key=api_key)

    contenidos = []
    if historial:
        for m in historial:
            rol = 'user' if m['role'] == 'user' else 'model'
            contenidos.append(types.Content(role=rol, parts=[types.Part(text=m['content'])]))

    contenidos.append(types.Content(role='user', parts=[types.Part(text=pregunta_usuario)]))

    try:
        respuesta = cliente.models.generate_content(
            model="gemini-3.6-flash",
            contents=contenidos,
            config=types.GenerateContentConfig(
                system_instruction=INSTRUCCIONES_SISTEMA,
                max_output_tokens=500,
            )
        )
        return respuesta.text
    except Exception as e:
        current_app.logger.error(f"Error al consultar el asistente de IA: {e}")
        return "Hubo un problema al conectar con el asistente. Inténtalo de nuevo en unos minutos."