"""
Módulo de clasificación de riesgo (Sistema de Semáforo) - RespiraKids

⚠️ IMPORTANTE:
Las reglas de este archivo son PROVISIONALES (versión v0), con fines de prototipo.
Deben ser revisadas, ajustadas y validadas por un profesional de la salud
antes de cualquier uso con pacientes reales. Su comportamiento está fijado por
las pruebas de caracterización en tests/test_semaforo_v0.py.

Este sistema NO diagnostica enfermedades. Es una herramienta de orientación
y alerta temprana, no un reemplazo del criterio médico profesional.
"""

VERSION_REGLAS = 'v0-provisional'


def identificar_senales(registro):
    """
    Aplica las reglas a un RegistroSintomas y devuelve las posibles señales identificadas:
    {'rojo': [texto, ...], 'amarillo': [texto, ...]}
    """
    señales_alarma_rojo = []
    señales_alerta_amarillo = []

    # --- Posibles señales de alarma (nivel ROJO) ---
    if registro.dificultad_respiratoria:
        señales_alarma_rojo.append('dificultad respiratoria reportada')

    if registro.respiracion_rapida:
        señales_alarma_rojo.append('respiración rápida reportada')

    if registro.temperatura is not None and registro.temperatura >= 39.0:
        señales_alarma_rojo.append(f'temperatura elevada ({registro.temperatura}°C)')

    if registro.decaimiento and registro.perdida_apetito:
        señales_alarma_rojo.append('decaimiento marcado junto con pérdida de apetito')

    if registro.severidad is not None and registro.severidad >= 8:
        señales_alarma_rojo.append(f'severidad reportada muy alta ({registro.severidad}/10)')

    # --- Señales de mayor vigilancia (nivel AMARILLO) ---
    if registro.temperatura is not None and 38.0 <= registro.temperatura < 39.0:
        señales_alerta_amarillo.append(f'fiebre moderada ({registro.temperatura}°C)')

    if registro.tos:
        señales_alerta_amarillo.append('tos presente')

    if registro.congestion_nasal or registro.secrecion_nasal:
        señales_alerta_amarillo.append('congestión/secreción nasal')

    if registro.dolor_garganta:
        señales_alerta_amarillo.append('dolor de garganta')

    if registro.decaimiento:
        señales_alerta_amarillo.append('decaimiento')

    if registro.vomito or registro.diarrea:
        señales_alerta_amarillo.append('síntomas gastrointestinales (vómito/diarrea)')

    if registro.severidad is not None and 5 <= registro.severidad < 8:
        señales_alerta_amarillo.append(f'severidad moderada reportada ({registro.severidad}/10)')

    if registro.inicio_sintomas == 'mas_3_dias':
        señales_alerta_amarillo.append('síntomas presentes desde hace más de 3 días')

    if registro.estornudos:
        señales_alerta_amarillo.append('estornudos frecuentes')

    if registro.irritabilidad:
        señales_alerta_amarillo.append('irritabilidad')

    return {'rojo': señales_alarma_rojo, 'amarillo': señales_alerta_amarillo}


def clasificar_riesgo(registro):
    """
    Recibe un objeto RegistroSintomas y devuelve una tupla:
    (nivel_riesgo, motivo, recomendaciones)
    nivel_riesgo puede ser: 'verde', 'amarillo', 'rojo'
    """
    señales = identificar_senales(registro)

    # --- Decisión final ---
    if señales['rojo']:
        motivo = 'Se identificaron posibles señales de alarma: ' + ', '.join(señales['rojo']) + '.'
        recomendaciones = (
            'Se recomienda buscar atención médica oportunamente. '
            'Esta clasificación es orientativa y no reemplaza la evaluación de un profesional de la salud.'
        )
        return 'rojo', motivo, recomendaciones

    elif señales['amarillo']:
        motivo = 'Se identificaron síntomas que ameritan mayor vigilancia: ' + ', '.join(señales['amarillo']) + '.'
        recomendaciones = (
            'Se recomienda observar la evolución del niño/a de forma cercana en las próximas horas '
            'y considerar asesoría de un profesional de la salud si los síntomas persisten o empeoran.'
        )
        return 'amarillo', motivo, recomendaciones

    else:
        motivo = 'No se identificaron síntomas relevantes en este registro.'
        recomendaciones = (
            'Continuar con medidas preventivas generales y seguimiento habitual.'
        )
        return 'verde', motivo, recomendaciones
