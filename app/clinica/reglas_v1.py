"""Reglas clínicas v1 de RespiraKids, basadas en la Herramienta Clínica de la primera infancia
(AIEPI clínico) del Ministerio de Salud y Protección Social de Colombia.

ESTADO: PENDIENTES DE VALIDACIÓN POR UN PROFESIONAL DE SALUD. No usar en producción hasta que
un profesional firme esta versión (ver `ProductionConfig` y docs/REGLAS_CLINICAS_v1.md).

Principios:
1. Cada criterio se toma literalmente del documento maestro de conocimiento clínico; se cita
   en `criterio` y se enlaza en `fuente`.
2. La fuente NO define una semaforización verde/amarillo/rojo (documento maestro, sección 15).
   RespiraKids aplica una única convención de mapeo, que es la decisión principal a validar:
     - ROJO: signos que la fuente describe como signos de alarma, de gravedad, de máxima
       gravedad, o para los que indica hospitalización o remisión hospitalaria.
     - AMARILLO: hallazgos para los que la fuente indica consultar/canalizar, o clasificaciones
       no graves (p. ej. "Neumonía", "Tos ferina").
     - VERDE: no se identificó ningún criterio anterior. No significa "sano".
3. Lo que la fuente no especifica no se completa: se informa como aviso o se documenta como
   regla no implementable.
4. Las reglas de salvaguarda (origen='salvaguarda') NO provienen de la fuente; existen por
   seguridad del usuario y están marcadas de forma explícita.
"""
from dataclasses import dataclass, field
from typing import Callable

VERSION = 'v1-aiepi'

MAPEO_COLOR = (
    'La asignación de color es una convención de RespiraKids (la fuente no define semaforización): '
    'confirmar que el nivel asignado es adecuado.'
)


@dataclass(frozen=True)
class Regla:
    id: str
    nivel: str                      # 'rojo' o 'amarillo'
    senal: str                      # texto para el cuidador (sin lenguaje de diagnóstico)
    criterio: str                   # criterio de la fuente, citado
    fuente: str                     # clave en clinica/fuentes.py
    orientacion: str                # qué indica la fuente hacer
    condicion: Callable = field(repr=False, compare=False)
    origen: str = 'fuente'          # 'fuente' o 'salvaguarda'
    validacion: tuple = ()          # puntos concretos que un profesional debe confirmar

    def aplica(self, datos):
        return bool(self.condicion(datos))


# ---------------------------------------------------------------- Umbrales literales de la fuente

def umbral_taquipnea(edad_meses):
    """Frecuencia respiratoria por encima de la cual hay taquipnea (Módulo 6 · Neumonía).

    Fuente: "<2 meses >60; 3-12 meses >50; 1-5 años >40". Devuelve None si la fuente no
    especifica umbral para la edad (de 2 a <3 meses).
    """
    if edad_meses < 2:
        return 60
    if edad_meses < 3:
        return None  # la fuente no especifica umbral entre 2 y 3 meses
    if edad_meses < 12:
        return 50
    return 40        # 12 meses = 1 año: se aplica la banda "1-5 años" (ver validación de A01)


def umbral_hipoxemia(altitud_msnm):
    """Saturación de O2 igual o inferior a la cual hay hipoxemia según la altitud (Módulo 6 · Neumonía).

    Fuente: "0-1500 msnm ≤94%; 1501-2000 ≤92%; 2001-2500 ≤90%; 2501-3000 ≤88%; 3500-4000 ≤83%".
    Devuelve None si la fuente no especifica valor para esa altitud (3001-3499 o más de 4000 msnm).
    """
    for minimo, maximo, umbral in ((0, 1500, 94), (1501, 2000, 92), (2001, 2500, 90),
                                   (2501, 3000, 88), (3500, 4000, 83)):
        if minimo <= altitud_msnm <= maximo:
            return umbral
    return None


def tiene_taquipnea(d):
    if d.frecuencia_respiratoria is None:
        return False
    umbral = umbral_taquipnea(d.edad_meses)
    return umbral is not None and d.frecuencia_respiratoria > umbral


def tiene_hipoxemia(d):
    if d.spo2 is None or d.altitud_msnm is None:
        return False
    umbral = umbral_hipoxemia(d.altitud_msnm)
    return umbral is not None and d.spo2 <= umbral


def caso_probable_tos_ferina(d):
    """Definición clínica de caso probable según edad (Protocolo INS, citado en Módulo 6 · Tos ferina)."""
    if d.edad_meses < 3:
        # "Todas las IRA con al menos uno de: accesos de tos (tos paroxística), estridor, apnea, cianosis,
        #  vómitos por acceso de tos."
        return d.tiene_ira and (d.tos_paroxistica or d.estridor or d.apnea or d.cianosis or d.vomito_tras_tos)
    # 3 meses a 12 años: "Tos paroxística intensa de cualquier duración acompañada por estridor o, en ausencia
    # de diagnóstico más probable, todas las IRA con tos >7 días y uno o más de: tos paroxística, estridor,
    # vómitos por acceso de tos."
    paroxistica_con_estridor = d.tos_paroxistica and d.estridor
    tos_prolongada = (d.tiene_ira and (d.dias_tos or 0) > 7
                      and (d.tos_paroxistica or d.estridor or d.vomito_tras_tos))
    return paroxistica_con_estridor or tos_prolongada


# ---------------------------------------------------------------- Reglas

_SIGNO_MAXIMA_GRAVEDAD = ('"Signos de máxima gravedad o predictivos de muerte: cianosis, incapacidad de ingerir '
                          'líquidos, quejido, aleteo nasal y desnutrición aguda."')
ORIENTACION_ALARMA = ('La fuente describe este hallazgo como signo de alarma o de gravedad. '
                       'Busca atención en un servicio de salud de inmediato.')
_OBSERVADO_POR_CUIDADOR = 'Signo observado por el cuidador, no verificado por un profesional: confirmar que es adecuado usarlo así.'

REGLAS = (
    # ------------------------------------------------------------ ROJO
    Regla(
        id='R01', nivel='rojo', senal='Tiraje subcostal (hundimiento debajo de las costillas al respirar)',
        criterio='Neumonía: "se confiere gravedad cuando presenta tiraje subcostal independientemente de la '
                 'frecuencia respiratoria". Listado también como signo de alarma en Neumonía y Bronquiolitis.',
        fuente='neumonia', orientacion=ORIENTACION_ALARMA,
        condicion=lambda d: d.tiraje_subcostal,
        validacion=(MAPEO_COLOR, _OBSERVADO_POR_CUIDADOR),
    ),
    Regla(
        id='R02', nivel='rojo', senal='Coloración azulada de labios o piel (cianosis)',
        criterio=f'Neumonía: {_SIGNO_MAXIMA_GRAVEDAD} También es signo de alarma en Bronquiolitis y CRUP.',
        fuente='neumonia', orientacion=ORIENTACION_ALARMA,
        condicion=lambda d: d.cianosis,
        validacion=(MAPEO_COLOR, _OBSERVADO_POR_CUIDADOR),
    ),
    Regla(
        id='R03', nivel='rojo', senal='No puede beber líquidos',
        criterio=f'Neumonía: {_SIGNO_MAXIMA_GRAVEDAD}',
        fuente='neumonia', orientacion=ORIENTACION_ALARMA,
        condicion=lambda d: d.incapacidad_beber_liquidos,
        validacion=(MAPEO_COLOR,),
    ),
    Regla(
        id='R04', nivel='rojo', senal='Quejido al respirar',
        criterio=f'Neumonía: {_SIGNO_MAXIMA_GRAVEDAD}',
        fuente='neumonia', orientacion=ORIENTACION_ALARMA,
        condicion=lambda d: d.quejido,
        validacion=(MAPEO_COLOR, _OBSERVADO_POR_CUIDADOR),
    ),
    Regla(
        id='R05', nivel='rojo', senal='Aleteo nasal',
        criterio=f'Neumonía: {_SIGNO_MAXIMA_GRAVEDAD}',
        fuente='neumonia', orientacion=ORIENTACION_ALARMA,
        condicion=lambda d: d.aleteo_nasal,
        validacion=(MAPEO_COLOR, _OBSERVADO_POR_CUIDADOR),
    ),
    Regla(
        id='R06', nivel='rojo', senal='Pausas en la respiración (apnea)',
        criterio='Bronquiolitis, signos de alarma: "Tiraje subcostal, respiración rápida, apneas, cianosis, '
                 'saturación de oxígeno baja según edad y altura. Factores de BAR."',
        fuente='bronquiolitis', orientacion=ORIENTACION_ALARMA,
        condicion=lambda d: d.apnea,
        validacion=(MAPEO_COLOR, _OBSERVADO_POR_CUIDADOR),
    ),
    Regla(
        id='R07', nivel='rojo', senal='Saturación de oxígeno baja para la altitud (hipoxemia)',
        criterio='Neumonía: "Oximetría según altitud (hipoxemia): 0-1500 msnm ≤94%; 1501-2000 ≤92%; '
                 '2001-2500 ≤90%; 2501-3000 ≤88%; 3500-4000 ≤83%." La hipoxemia según altitud está en sus '
                 'signos de alarma.',
        fuente='neumonia', orientacion=ORIENTACION_ALARMA,
        condicion=tiene_hipoxemia,
        validacion=(MAPEO_COLOR,
                    'La fuente no da umbral para 3001-3499 msnm ni para más de 4000 msnm; en esos casos la '
                    'regla no se aplica y se muestra un aviso.',
                    'Confirmar si la medición con oxímetro doméstico por parte del cuidador es aceptable.'),
    ),
    Regla(
        id='R08', nivel='rojo', senal='Estridor en reposo (ruido agudo al inhalar estando tranquilo/a)',
        criterio='CRUP, signos de alarma: "Estridor en reposo, tirajes moderados o graves, ventilación disminuida '
                 'o muy disminuida, cianosis (con agitación o en reposo), alteración del nivel de conciencia."',
        fuente='crup', orientacion=ORIENTACION_ALARMA,
        condicion=lambda d: d.estridor,
        validacion=(MAPEO_COLOR, _OBSERVADO_POR_CUIDADOR,
                    'El formulario pregunta específicamente por estridor EN REPOSO.'),
    ),
    Regla(
        id='R09', nivel='rojo', senal='Alteración de la conciencia (muy somnoliento/a o difícil de despertar)',
        criterio='CRUP, signos de alarma: "alteración del nivel de conciencia". Enfermedad febril, signos de '
                 'alarma: "alteración de conciencia".',
        fuente='crup', orientacion=ORIENTACION_ALARMA,
        condicion=lambda d: d.alteracion_conciencia,
        validacion=(MAPEO_COLOR, _OBSERVADO_POR_CUIDADOR),
    ),
    Regla(
        id='R10', nivel='rojo', senal='Convulsión',
        criterio='Enfermedad febril, signos de alarma: "convulsiones a repetición". Tos ferina, complicaciones: '
                 '"convulsiones".',
        fuente='fiebre', orientacion=ORIENTACION_ALARMA,
        condicion=lambda d: d.convulsion,
        validacion=(MAPEO_COLOR,
                    'La fuente dice "convulsiones a repetición"; el formulario registra cualquier convulsión. '
                    'Confirmar si un único episodio debe clasificarse en rojo.'),
    ),
    Regla(
        id='R11', nivel='rojo', senal='Temperatura mayor de 40 °C',
        criterio='Enfermedad febril, signos de alarma: "temperatura >40°C".',
        fuente='fiebre', orientacion=ORIENTACION_ALARMA,
        condicion=lambda d: d.temperatura is not None and d.temperatura > 40,
        validacion=(MAPEO_COLOR,),
    ),
    Regla(
        id='R12', nivel='rojo', senal='Rigidez de cuello',
        criterio='Enfermedad febril, signos de alarma (signos de localización graves): "rigidez de cuello".',
        fuente='fiebre', orientacion=ORIENTACION_ALARMA,
        condicion=lambda d: d.rigidez_cuello,
        validacion=(MAPEO_COLOR, _OBSERVADO_POR_CUIDADOR),
    ),
    Regla(
        id='R13', nivel='rojo', senal='Fontanela abombada (la "mollera" levantada)',
        criterio='Enfermedad febril, signos de alarma (signos de localización graves): "abombamiento de fontanela".',
        fuente='fiebre', orientacion=ORIENTACION_ALARMA,
        condicion=lambda d: d.abombamiento_fontanela,
        validacion=(MAPEO_COLOR, _OBSERVADO_POR_CUIDADOR),
    ),
    Regla(
        id='R14', nivel='rojo', senal='Manchas rojas o moradas en la piel (púrpura o petequias)',
        criterio='Enfermedad febril, signos de alarma (signos de localización graves): "púrpura/petequias".',
        fuente='fiebre', orientacion=ORIENTACION_ALARMA,
        condicion=lambda d: d.petequias,
        validacion=(MAPEO_COLOR, _OBSERVADO_POR_CUIDADOR),
    ),
    Regla(
        id='R15', nivel='rojo', senal='Hinchazón y enrojecimiento detrás de la oreja',
        criterio='Otitis media aguda: "Edema y eritema retroauricular deben hacer sospechar mastoiditis." '
                 '"Mastoiditis se clasifica como enfermedad grave." "Mastoiditis debe ser remitida para manejo '
                 'hospitalario."',
        fuente='otitis',
        orientacion='La fuente indica que este hallazgo debe hacer sospechar una complicación que requiere manejo '
                    'hospitalario. Busca atención en un servicio de salud de inmediato.',
        condicion=lambda d: d.edema_retroauricular,
        validacion=(MAPEO_COLOR, _OBSERVADO_POR_CUIDADOR),
    ),
    Regla(
        id='R16', nivel='rojo', senal='Signos compatibles con la definición de caso probable de tos ferina en menor de 6 meses',
        criterio='Tos ferina: definición de caso probable según edad (Protocolo INS) y "Se sugiere hospitalización '
                 'en todos los menores de seis meses y en cualquier edad con enfermedad severa."',
        fuente='tos_ferina',
        orientacion='La fuente sugiere hospitalización en todos los menores de seis meses con este cuadro. '
                    'Busca atención en un servicio de salud de inmediato.',
        condicion=lambda d: d.edad_meses < 6 and caso_probable_tos_ferina(d),
        validacion=(MAPEO_COLOR,
                    'La definición de caso probable la aplica normalmente un profesional; aquí se usa con datos '
                    'reportados por el cuidador.',
                    'Para menores de 3 meses, "todas las IRA" se interpreta como cualquier registro con síntomas '
                    'respiratorios.'),
    ),
    Regla(
        id='R17', nivel='rojo', senal='Sibilancias en menor de 2 años con factores de alto riesgo',
        criterio='Bronquiolitis: BAR cuando en niños <2 años con sospecha de bronquiolitis se asocian "<2 meses; '
                 'prematuridad (peso <2000 g al nacer) en <6 meses; enfermedades congénitas cardiovasculares...; '
                 'presencia de apneas; desnutrición aguda grave". Signos de alarma: "... Factores de BAR."',
        fuente='bronquiolitis', orientacion=ORIENTACION_ALARMA,
        condicion=lambda d: d.sibilancias and d.edad_meses < 24 and (d.edad_meses < 2 or d.factor_riesgo_bar or d.apnea),
        validacion=(MAPEO_COLOR,
                    'La fuente define bronquiolitis como el PRIMER episodio de sibilancias; el formulario no '
                    'distingue si es el primero.',
                    'Los factores de BAR se preguntan en una sola casilla que lista los de la fuente.'),
    ),

    # ------------------------------------------------------------ AMARILLO
    Regla(
        id='A01', nivel='amarillo', senal='Respiración rápida para la edad (frecuencia respiratoria medida)',
        criterio='Neumonía: "Taquipnea es el mejor signo único predictor de neumonía (OMS)." "Valores de '
                 'frecuencia respiratoria (taquipnea): <2 meses >60; 3-12 meses >50; 1-5 años >40. Medir por '
                 '1 minuto, niño despierto sin llorar." Clasificación de la fuente: "Neumonía grave – Neumonía".',
        fuente='neumonia',
        orientacion='La fuente indica que la respiración rápida para la edad debe ser valorada por un profesional '
                    'de salud. Consulta pronto.',
        condicion=tiene_taquipnea,
        validacion=(MAPEO_COLOR,
                    'Sin tiraje ni signos de máxima gravedad se asigna amarillo (clasificación "Neumonía", no '
                    '"Neumonía grave"). En Bronquiolitis la fuente lista la respiración rápida entre los signos de '
                    'alarma: confirmar el nivel.',
                    'La fuente no da umbral entre 2 y 3 meses; ahí la regla no se aplica y se muestra un aviso.',
                    'A los 12 meses exactos las bandas "3-12 meses" y "1-5 años" se solapan; se usa >40.'),
    ),
    Regla(
        id='A02', nivel='amarillo', senal='Signos compatibles con la definición de caso probable de tos ferina',
        criterio='Tos ferina: definición de caso probable según edad (Protocolo INS). Clasificación de la fuente: '
                 '"Tos ferina grave – Tos ferina". "Notificar caso probable". "Canalizar a especialista en pediatría".',
        fuente='tos_ferina',
        orientacion='La fuente indica que estos casos deben ser valorados y notificados por un profesional de salud. '
                    'Consulta pronto a un servicio de salud.',
        condicion=lambda d: d.edad_meses >= 6 and caso_probable_tos_ferina(d),
        validacion=(MAPEO_COLOR,),
    ),
    Regla(
        id='A03', nivel='amarillo', senal='Tos por más de 15 días',
        criterio='Tuberculosis, cuándo consultar: "Ante tos de más de 15 días con o sin expectoración, fiebre >8 días, '
                 'pérdida o no ganancia de peso, disminución de la actividad o juego, y contacto con un caso de '
                 'tuberculosis."',
        fuente='tuberculosis', orientacion='La fuente indica consultar a un profesional de salud ante este hallazgo.',
        condicion=lambda d: (d.dias_tos or 0) > 15,
        validacion=(MAPEO_COLOR,
                    'La fuente enumera los criterios unidos por "y"; RespiraKids aplica cada uno por separado (más '
                    'sensible). Confirmar si deben exigirse combinados.'),
    ),
    Regla(
        id='A04', nivel='amarillo', senal='Fiebre por más de 7 días',
        criterio='Enfermedad febril, cuándo consultar: "Ante signos de enfermedad grave, signos de localización, '
                 'fiebre prolongada (>7 días) o condiciones de riesgo." Tuberculosis: "fiebre >8 días".',
        fuente='fiebre', orientacion='La fuente indica consultar a un profesional de salud ante fiebre prolongada.',
        condicion=lambda d: (d.dias_fiebre or 0) > 7,
        validacion=(MAPEO_COLOR,),
    ),
    Regla(
        id='A05', nivel='amarillo', senal='Contacto con una persona con tuberculosis',
        criterio='Tuberculosis, cuándo consultar: "... y contacto con un caso de tuberculosis." Factores de riesgo: '
                 '"Contacto domiciliario o estrecho con caso de tuberculosis pulmonar; niños y niñas menores de 5 años".',
        fuente='tuberculosis', orientacion='La fuente indica consultar a un profesional de salud ante este antecedente.',
        condicion=lambda d: d.contacto_tuberculosis,
        validacion=(MAPEO_COLOR, 'Mismo punto de A03 sobre criterios combinados.'),
    ),
    Regla(
        id='A06', nivel='amarillo', senal='Pérdida de peso o no ganancia de peso',
        criterio='Tuberculosis, cuándo consultar: "pérdida o no ganancia de peso".',
        fuente='tuberculosis', orientacion='La fuente indica consultar a un profesional de salud ante este hallazgo.',
        condicion=lambda d: d.perdida_peso,
        validacion=(MAPEO_COLOR, 'Mismo punto de A03 sobre criterios combinados.'),
    ),
    Regla(
        id='A07', nivel='amarillo', senal='Disminución de la actividad o del juego',
        criterio='Tuberculosis, cuándo consultar: "disminución de la actividad o juego".',
        fuente='tuberculosis', orientacion='La fuente indica consultar a un profesional de salud ante este hallazgo.',
        condicion=lambda d: d.disminucion_actividad,
        validacion=(MAPEO_COLOR, 'Mismo punto de A03 sobre criterios combinados.'),
    ),
    Regla(
        id='A08', nivel='amarillo', senal='Sibilancias (silbido en el pecho) en menor de 2 años',
        criterio='Bronquiolitis: "primer episodio de sibilancias en un lactante menor de 2 años precedido de cuadro '
                 'gripal". Clasificación de la fuente: "Bronquiolitis – Bronquiolitis Grave – Síndrome sibilante '
                 'recurrente". "Canalizar a especialista en pediatría según disponibilidad cuando haya factores de '
                 'riesgo o complicaciones."',
        fuente='bronquiolitis',
        orientacion='Consulta a un profesional de salud para que valore las sibilancias.',
        condicion=lambda d: d.sibilancias and d.edad_meses < 24,
        validacion=(MAPEO_COLOR, _OBSERVADO_POR_CUIDADOR),
    ),

    # ------------------------------------------------------------ SALVAGUARDA (no proviene de la fuente)
    Regla(
        id='S01', nivel='amarillo',
        senal='Dificultad para respirar o respiración rápida reportada por el cuidador (sin medir)',
        criterio='NO PROVIENE DE LA FUENTE. La fuente menciona la dificultad respiratoria como componente de '
                 'Bronquiolitis, CRUP y Asma, y exige MEDIR la frecuencia respiratoria durante 1 minuto; no '
                 'clasifica la percepción del cuidador por sí sola.',
        fuente='respirakids', origen='salvaguarda',
        orientacion='Indicaste dificultad para respirar o respiración rápida. Si puedes, cuenta las respiraciones '
                    'durante 1 minuto, revisa los signos de alarma y consulta a un profesional de salud.',
        condicion=lambda d: (d.dificultad_respiratoria or d.respiracion_rapida) and not tiene_taquipnea(d),
        validacion=('Regla de salvaguarda: decidir si se conserva, se cambia de nivel o se elimina.',),
    ),
)

REGLAS_POR_ID = {r.id: r for r in REGLAS}

# Criterios de la fuente que no se pueden aplicar con los datos que registra un cuidador.
NO_IMPLEMENTABLES = (
    ('Desnutrición aguda (Neumonía, Bronquiolitis)', 'Requiere valoración antropométrica por un profesional.'),
    ('Mal estado clínico / triángulo de aproximación pediátrica alterado (Fiebre)', 'Requiere examen por un profesional.'),
    ('Hipotermia en niño pequeño o desnutrido (Fiebre)', 'La fuente no especifica umbral de temperatura ni de edad.'),
    ('Edad como factor de riesgo de bacteriemia oculta (Fiebre)', 'La fuente no especifica umbral de edad.'),
    ('Choque (Fiebre)', 'Requiere examen por un profesional.'),
    ('Escala de Westley para CRUP (tirajes, ventilación, cianosis, conciencia)', 'Requiere auscultación con fonendoscopio.'),
    ('Tirajes moderados o graves y ventilación disminuida (CRUP)', 'Requiere examen por un profesional.'),
    ('Crépitos y signos de consolidación (Neumonía)', 'Requiere auscultación.'),
    ('Signos de severidad de rinosinusitis y complicaciones orbitarias', 'Requiere examen; la fuente no define nivel.'),
    ('Clasificación de otitis, faringoamigdalitis y asma (IPA)', 'Requiere examen o historia clínica completa.'),
    ('Taquipnea entre 2 y 3 meses de edad', 'La fuente no especifica umbral para esa edad.'),
    ('Hipoxemia entre 3001 y 3499 msnm o por encima de 4000 msnm', 'La fuente no especifica umbral para esas altitudes.'),
)
