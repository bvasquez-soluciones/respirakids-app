"""
Módulo del Asistente de IA - RespiraKids

Este asistente resuelve dudas generales de prevención y cuidados básicos.
NO diagnostica, NO prescribe medicamentos, NO sustituye al médico.
"""

import os
from google import genai
from google.genai import types
from flask import current_app

# Modelo de Gemini a usar. gemini-1.5-flash y gemini-2.5-flash fueron
# descontinuados por Google para cuentas nuevas (Google ya no los ofrece y
# recomienda gemini-3.6-flash). Se puede sobreescribir con la variable de
# entorno GEMINI_MODEL sin tocar código si Google vuelve a cambiar el
# modelo recomendado.
MODELO_GEMINI = os.getenv('GEMINI_MODEL', 'gemini-3.6-flash')


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
el criterio de un profesional de la salud.

FORMATO DE TUS RESPUESTAS:
- Cuando dés una lista de medidas o recomendaciones generales, usa líneas que empiecen con "- " (guion y espacio), una por línea.
- Si la situación amerita una nota de precaución o de cuándo buscar atención médica, ponla en su propia línea comenzando exactamente con "⚠️ Atención:".
- Usa **negrita** (con doble asterisco) solo para resaltar palabras clave puntuales, no frases completas.
- Sé breve: prefiere respuestas de 3 a 6 líneas en total, salvo que el usuario pida más detalle."""


def preguntar_asistente(pregunta_usuario, historial=None):
    """
    Envía una pregunta al asistente de IA y devuelve la respuesta como texto.
    """
    api_key = current_app.config.get('GEMINI_API_KEY') or os.getenv('GEMINI_API_KEY')

    if not api_key:
        print("❌ ERROR: No se encontró GEMINI_API_KEY.")
        return "El asistente de IA no está configurado. Por favor contacta al administrador del sistema."

    try:
        client = genai.Client(api_key=api_key.strip())

        # Construir el historial como una lista de turnos (user/model), que es
        # el formato multi-turno real de la API, en vez de un solo string plano.
        contenidos = []
        if historial:
            for m in historial:
                rol = "user" if m.get('role') == 'user' else "model"
                contenidos.append(
                    types.Content(role=rol, parts=[types.Part(text=m.get('content', ''))])
                )
        contenidos.append(
            types.Content(role="user", parts=[types.Part(text=pregunta_usuario)])
        )

        response = client.models.generate_content(
            model=MODELO_GEMINI,
            contents=contenidos,
            config=types.GenerateContentConfig(
                system_instruction=INSTRUCCIONES_SISTEMA
            ),
        )
        return response.text

    except Exception as e:
        print(f"❌ ERROR EN GEMINI: {e}")
        current_app.logger.error(f"Error al consultar el asistente de IA: {e}")
        return "Hubo un problema al conectar con el asistente. Inténtalo de nuevo en unos minutos."