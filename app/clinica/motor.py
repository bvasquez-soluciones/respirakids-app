"""Motor de evaluación clínica: aplica el conjunto de reglas vigente a un registro de síntomas."""
import json
from dataclasses import dataclass, field, fields

from flask import current_app

from app.clinica import reglas_v1
from app.clinica.fuentes import fuente
from app.semaforo import VERSION_REGLAS as VERSION_V0
from app.semaforo import clasificar_riesgo, identificar_senales

ORDEN = {'verde': 0, 'amarillo': 1, 'rojo': 2}

ORIENTACION_GENERAL = {
    'rojo': 'Se identificaron signos que la fuente clínica describe como signos de alarma o de gravedad. '
            'Busca atención en un servicio de salud de inmediato.',
    'amarillo': 'Se identificaron hallazgos para los que la fuente clínica indica valoración por un profesional '
                'de salud. Consulta pronto y vigila si aparecen signos de alarma.',
    'verde': 'En este registro no se identificaron los signos de alarma ni los criterios de consulta descritos en '
             'la fuente clínica. Esto no significa que no haya enfermedad: observa la evolución y registra de nuevo '
             'o consulta si aparecen nuevos síntomas o empeora.',
}
PREVENCION = ('Medida preventiva descrita en la fuente: el lavado frecuente de manos de quienes cuidan a los niños '
              '(Módulo 6 · Rinofaringitis aguda).')

_CAMPOS_RESPIRATORIOS = (
    'tos', 'dificultad_respiratoria', 'respiracion_rapida', 'congestion_nasal', 'secrecion_nasal',
    'dolor_garganta', 'estornudos', 'sibilancias', 'estridor', 'tiraje_subcostal', 'tos_paroxistica',
)


@dataclass
class DatosEvaluacion:
    """Datos de entrada del motor: lo registrado por el cuidador más la edad del niño en la fecha del registro."""
    edad_meses: int
    temperatura: float = None
    frecuencia_respiratoria: int = None
    spo2: float = None
    altitud_msnm: int = None
    dias_tos: int = None
    dias_fiebre: int = None
    tos: bool = False
    dificultad_respiratoria: bool = False
    respiracion_rapida: bool = False
    congestion_nasal: bool = False
    secrecion_nasal: bool = False
    dolor_garganta: bool = False
    estornudos: bool = False
    sibilancias: bool = False
    estridor: bool = False
    tiraje_subcostal: bool = False
    cianosis: bool = False
    incapacidad_beber_liquidos: bool = False
    aleteo_nasal: bool = False
    quejido: bool = False
    apnea: bool = False
    convulsion: bool = False
    alteracion_conciencia: bool = False
    rigidez_cuello: bool = False
    abombamiento_fontanela: bool = False
    petequias: bool = False
    edema_retroauricular: bool = False
    tos_paroxistica: bool = False
    vomito_tras_tos: bool = False
    contacto_tuberculosis: bool = False
    perdida_peso: bool = False
    disminucion_actividad: bool = False
    factor_riesgo_bar: bool = False

    @classmethod
    def desde_registro(cls, registro, nino):
        valores = {}
        for f in fields(cls):
            if f.name == 'edad_meses':
                continue
            valor = getattr(registro, f.name, None)
            valores[f.name] = bool(valor) if f.type is bool else valor
        fecha = registro.fecha.date() if registro.fecha else None
        return cls(edad_meses=nino.edad_meses(fecha), **valores)

    @property
    def tiene_ira(self):
        """Hay al menos un síntoma o signo respiratorio registrado."""
        return any(getattr(self, campo) for campo in _CAMPOS_RESPIRATORIOS)


@dataclass
class Resultado:
    nivel: str
    version: str
    senales: list = field(default_factory=list)       # dicts: regla_id, nivel, texto, fuente, origen, pendiente_validacion
    avisos: list = field(default_factory=list)        # información que no cambia el nivel
    orientaciones: list = field(default_factory=list)
    pendiente_validacion: bool = True

    @property
    def motivo(self):
        if not self.senales:
            return 'No se identificaron criterios de la fuente clínica en este registro.'
        return 'Posibles señales identificadas: ' + '; '.join(s['texto'] for s in self.senales) + '.'

    @property
    def recomendaciones(self):
        return ' '.join(self.orientaciones)

    def detalle_json(self):
        """Lo que se persiste en la evaluación para poder mostrarla tal como se emitió."""
        return json.dumps({'senales': self.senales, 'avisos': self.avisos}, ensure_ascii=False)


# ---------------------------------------------------------------- v1 (AIEPI)

def _avisos(d):
    avisos = []
    if d.frecuencia_respiratoria is not None and reglas_v1.umbral_taquipnea(d.edad_meses) is None:
        avisos.append('La fuente clínica no especifica el valor de respiración rápida para niños entre 2 y 3 meses; '
                      'la frecuencia respiratoria registrada no se pudo interpretar. Consulta a un profesional.')
    if d.spo2 is not None and d.altitud_msnm is None:
        avisos.append('Registraste la saturación de oxígeno sin la altitud del lugar; no se pudo interpretar.')
    elif d.spo2 is not None and reglas_v1.umbral_hipoxemia(d.altitud_msnm) is None:
        avisos.append('La fuente clínica no especifica el valor de saturación para la altitud registrada; '
                      'no se pudo interpretar.')
    if d.temperatura is not None and d.temperatura > 38:
        avisos.append('La fuente considera fiebre una temperatura superior a 38 °C. Consulta si dura más de 7 días '
                      'o si aparecen signos de alarma (Módulo 5 · Enfermedad febril).')
    return avisos


def evaluar_v1(datos):
    aplicadas = [r for r in reglas_v1.REGLAS if r.aplica(datos)]
    nivel = max((r.nivel for r in aplicadas), key=ORDEN.get, default='verde')

    senales = [{
        'regla_id': r.id,
        'nivel': r.nivel,
        'texto': r.senal,
        'fuente': fuente(r.fuente),
        'origen': r.origen,
        'pendiente_validacion': True,
    } for r in sorted(aplicadas, key=lambda r: -ORDEN[r.nivel])]

    # Solo las orientaciones del nivel final: en rojo no se mezclan indicaciones de "consultar pronto".
    orientaciones = [ORIENTACION_GENERAL[nivel]]
    for r in aplicadas:
        if r.nivel == nivel and r.orientacion not in orientaciones and r.orientacion != reglas_v1.ORIENTACION_ALARMA:
            orientaciones.append(r.orientacion)
    if nivel == 'verde':
        orientaciones.append(PREVENCION)

    return Resultado(nivel=nivel, version=reglas_v1.VERSION, senales=senales, avisos=_avisos(datos),
                     orientaciones=orientaciones, pendiente_validacion=True)


# ---------------------------------------------------------------- v0 (provisional, histórico)

def evaluar_v0(registro):
    nivel, motivo, recomendaciones = clasificar_riesgo(registro)
    agrupadas = identificar_senales(registro)
    senales = [{'regla_id': None, 'nivel': n, 'texto': texto.capitalize(), 'fuente': None,
                'origen': 'provisional', 'pendiente_validacion': True}
               for n in ('rojo', 'amarillo') for texto in agrupadas[n]]
    return Resultado(nivel=nivel, version=VERSION_V0, senales=senales, orientaciones=[recomendaciones])


# ---------------------------------------------------------------- Punto de entrada

VERSIONES = {reglas_v1.VERSION, VERSION_V0}


def version_vigente():
    return current_app.config.get('MOTOR_CLINICO_VERSION', reglas_v1.VERSION)


def evaluar(registro, nino, version=None):
    version = version or version_vigente()
    if version == reglas_v1.VERSION:
        return evaluar_v1(DatosEvaluacion.desde_registro(registro, nino))
    if version == VERSION_V0:
        return evaluar_v0(registro)
    raise ValueError(f'Versión de reglas desconocida: {version}')
