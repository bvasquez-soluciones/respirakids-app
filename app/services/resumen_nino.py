"""Resumen del estado de un niño/a para el dashboard, la ficha y el historial."""
from dataclasses import dataclass, field

from app.clinica.motor import evaluar_v0
from app.fechas import fecha_hora_corta
from app.models import Evaluacion, MedicamentoRecetado, Receta, RegistroSintomas
from app.presentacion import hallazgos_registrados, nivel_info


@dataclass
class ResumenNino:
    nino: object
    ultima_evaluacion: object = None
    ultimo_registro: object = None
    senales: list = field(default_factory=list)
    hallazgos: list = field(default_factory=list)
    medicamentos_activos: list = field(default_factory=list)
    total_registros: int = 0

    @property
    def nivel(self):
        return self.ultima_evaluacion.nivel_riesgo if self.ultima_evaluacion else 'neutro'

    @property
    def info_nivel(self):
        return nivel_info(self.nivel)

    @property
    def senales_del_nivel(self):
        """Señales que explican el nivel actual (las de mayor nivel)."""
        return [s for s in self.senales if s['nivel'] == self.nivel]


def senales_de_evaluacion(evaluacion):
    """Posibles señales de una evaluación, tal como se emitieron (lista de dicts con nivel, texto y fuente).

    Las evaluaciones v1 guardan sus señales; las anteriores (v0) se reconstruyen con las reglas v0,
    que no han cambiado desde que se emitieron.
    """
    if not evaluacion:
        return []
    if evaluacion.detalle:
        return evaluacion.detalle.get('senales', [])
    if evaluacion.registro_sintomas:
        return evaluar_v0(evaluacion.registro_sintomas).senales
    return []


def avisos_de_evaluacion(evaluacion):
    return (evaluacion.detalle or {}).get('avisos', []) if evaluacion else []


def medicamentos_activos(nino):
    """Medicamentos activos indicados por un profesional (con su receta) para el niño."""
    return (
        MedicamentoRecetado.query
        .join(Receta, Receta.id == MedicamentoRecetado.receta_id)
        .filter(Receta.nino_id == nino.id, Receta.activa.is_(True), MedicamentoRecetado.activo.is_(True))
        .order_by(MedicamentoRecetado.fecha_inicio.desc())
        .all()
    )


def resumir(nino):
    ultima = (
        Evaluacion.query.filter_by(nino_id=nino.id)
        .order_by(Evaluacion.fecha.desc(), Evaluacion.id.desc())
        .first()
    )
    ultimo_registro = (
        RegistroSintomas.query.filter_by(nino_id=nino.id)
        .order_by(RegistroSintomas.fecha.desc(), RegistroSintomas.id.desc())
        .first()
    )
    return ResumenNino(
        nino=nino,
        ultima_evaluacion=ultima,
        ultimo_registro=ultimo_registro,
        senales=senales_de_evaluacion(ultima),
        hallazgos=hallazgos_registrados(ultimo_registro) if ultimo_registro else [],
        medicamentos_activos=medicamentos_activos(nino),
        total_registros=RegistroSintomas.query.filter_by(nino_id=nino.id).count(),
    )


def resumir_todos(ninos):
    """Resúmenes ordenados para que el niño con mayor nivel de riesgo aparezca primero."""
    resumenes = [resumir(n) for n in ninos]
    return sorted(resumenes, key=lambda r: (-r.info_nivel['orden'], r.nino.nombre))


def datos_evolucion(registros, maximo=30):
    """Serie para el gráfico de evolución: nivel de riesgo y temperatura, en orden cronológico."""
    puntos = sorted(registros, key=lambda r: r.fecha)[-maximo:]
    return {
        'etiquetas': [fecha_hora_corta(r.fecha) for r in puntos],
        'niveles': [nivel_info(r.evaluacion.nivel_riesgo)['orden'] if r.evaluacion else None for r in puntos],
        'temperaturas': [r.temperatura for r in puntos],
    }
