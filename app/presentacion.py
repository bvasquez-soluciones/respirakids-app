"""Presentación de la información clínica para los usuarios (fuente única de textos y etiquetas).

Este módulo NO clasifica: solo describe en lenguaje claro lo que decidió el motor clínico
(`app/clinica`) y lo que registró el cuidador. Nunca usa lenguaje de diagnóstico.
"""

AVISO_NO_DIAGNOSTICO = (
    'RespiraKids no constituye un diagnóstico médico y no reemplaza la valoración de un profesional de salud.'
)

# Textos por nivel. `titulo` es el mensaje principal para el cuidador; el color nunca va solo.
NIVELES = {
    'verde': {
        'nombre': 'Verde',
        'titulo': 'Sin señales de alarma identificadas',
        'resumen': 'Observa la evolución y registra de nuevo si aparecen síntomas o empeora.',
        'color': 'success',
        'icono': '🟢',
        'avatar': 'feliz',
        'orden': 1,
    },
    'amarillo': {
        'nombre': 'Amarillo',
        'titulo': 'Requiere vigilancia y seguimiento',
        'resumen': 'Consulta a un profesional de salud y vigila si aparecen signos de alarma.',
        'color': 'warning',
        'icono': '🟡',
        'avatar': 'preocupado',
        'orden': 2,
    },
    'rojo': {
        'nombre': 'Rojo',
        'titulo': 'Se identificaron posibles señales de alarma',
        'resumen': 'Se recomienda atención profesional.',
        'color': 'danger',
        'icono': '🔴',
        'avatar': 'enfermo',
        'orden': 3,
    },
    'neutro': {
        'nombre': 'Sin evaluación',
        'titulo': 'Aún no hay evaluaciones',
        'resumen': 'Registra los síntomas para obtener una orientación.',
        'color': 'secondary',
        'icono': '⚪',
        'avatar': 'normal',
        'orden': 0,
    },
}


def nivel_info(nivel):
    """Textos y estilos de un nivel de riesgo ('verde', 'amarillo', 'rojo' o None)."""
    return NIVELES.get(nivel or 'neutro', NIVELES['neutro'])


# Etiquetas de lo que el cuidador puede registrar, en el orden en que se muestran.
SINTOMAS_REPORTADOS = {
    'dificultad_respiratoria': 'Dificultad para respirar',
    'respiracion_rapida': 'Respiración rápida',
    'sibilancias': 'Silbido en el pecho (sibilancias)',
    'tos': 'Tos',
    'tos_paroxistica': 'Accesos de tos',
    'vomito_tras_tos': 'Vómito después de los accesos de tos',
    'congestion_nasal': 'Congestión nasal',
    'secrecion_nasal': 'Secreción nasal',
    'estornudos': 'Estornudos',
    'dolor_garganta': 'Dolor de garganta',
    'decaimiento': 'Decaimiento',
    'disminucion_actividad': 'Juega o se mueve menos de lo habitual',
    'perdida_apetito': 'Pérdida de apetito',
    'perdida_peso': 'Pérdida o no ganancia de peso',
    'irritabilidad': 'Irritabilidad',
    'vomito': 'Vómito',
    'diarrea': 'Diarrea',
}

SIGNOS_CLINICOS = {
    'tiraje_subcostal': 'Tiraje subcostal',
    'cianosis': 'Coloración azulada (cianosis)',
    'incapacidad_beber_liquidos': 'No puede beber líquidos',
    'aleteo_nasal': 'Aleteo nasal',
    'quejido': 'Quejido al respirar',
    'estridor': 'Estridor',
    'uso_musculos_accesorios': 'Uso de músculos accesorios',
    'apnea': 'Pausas en la respiración (apnea)',
    'convulsion': 'Convulsión',
    'palidez_extrema': 'Palidez extrema',
    'alteracion_conciencia': 'Alteración de la conciencia',
    'rigidez_cuello': 'Rigidez de cuello',
    'abombamiento_fontanela': 'Fontanela abombada',
    'petequias': 'Manchas rojas o moradas en la piel',
    'edema_retroauricular': 'Hinchazón y enrojecimiento detrás de la oreja',
}

INICIO_SINTOMAS = {
    'hoy': 'Hoy',
    'ayer': 'Ayer',
    '2_3_dias': 'Hace 2-3 días',
    'mas_3_dias': 'Hace más de 3 días',
}


def hallazgos_registrados(registro):
    """Lista de lo que el cuidador marcó en un registro (etiquetas legibles)."""
    hallazgos = [etiqueta for campo, etiqueta in SIGNOS_CLINICOS.items() if getattr(registro, campo, False)]
    hallazgos += [etiqueta for campo, etiqueta in SINTOMAS_REPORTADOS.items() if getattr(registro, campo, False)]
    if registro.temperatura is not None:
        hallazgos.append(f'Temperatura {registro.temperatura:.1f} °C')
    return hallazgos


def datos_complementarios(registro):
    """Información adicional del registro (duración, severidad percibida, antecedentes declarados)."""
    datos = []
    if registro.inicio_sintomas:
        datos.append(('Inicio de los síntomas', INICIO_SINTOMAS.get(registro.inicio_sintomas, registro.inicio_sintomas)))
    if registro.dias_sintomas is not None:
        datos.append(('Días con síntomas', str(registro.dias_sintomas)))
    if registro.dias_tos is not None:
        datos.append(('Días con tos', str(registro.dias_tos)))
    if registro.dias_fiebre is not None:
        datos.append(('Días con fiebre', str(registro.dias_fiebre)))
    if registro.severidad is not None:
        datos.append(('Malestar percibido por el cuidador', f'{registro.severidad}/10'))
    if registro.frecuencia_respiratoria is not None:
        datos.append(('Frecuencia respiratoria', f'{registro.frecuencia_respiratoria} por minuto'))
    if registro.spo2 is not None:
        altitud = f' a {registro.altitud_msnm} msnm' if registro.altitud_msnm is not None else ''
        datos.append(('Saturación de oxígeno', f'{registro.spo2:.0f} %{altitud}'))
    antecedentes = [t for c, t in (
        ('condicion_asma', 'asma'), ('condicion_alergias', 'alergias respiratorias'),
        ('contacto_tuberculosis', 'contacto con persona con tuberculosis'),
        ('factor_riesgo_bar', 'condición de riesgo para bronquiolitis'),
    ) if getattr(registro, c, False)]
    if antecedentes:
        datos.append(('Antecedentes declarados', ', '.join(antecedentes)))
    return datos
