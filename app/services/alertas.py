"""Pacientes con alerta roja para un profesional."""
from sqlalchemy import func

from app import db
from app.models import Autorizacion, Evaluacion, Nino, ahora_utc


def _ultimas_evaluaciones_subquery():
    return (
        db.session.query(Evaluacion.nino_id, func.max(Evaluacion.fecha).label('fecha'))
        .group_by(Evaluacion.nino_id)
        .subquery()
    )


def pacientes_en_rojo(profesional_id):
    """Lista de (nino, evaluacion) cuya evaluación más reciente es roja y el profesional tiene autorización activa."""
    ultimas = _ultimas_evaluaciones_subquery()
    return (
        db.session.query(Nino, Evaluacion)
        .join(Autorizacion, Autorizacion.nino_id == Nino.id)
        .join(ultimas, ultimas.c.nino_id == Nino.id)
        .join(Evaluacion, (Evaluacion.nino_id == Nino.id) & (Evaluacion.fecha == ultimas.c.fecha))
        .filter(
            Autorizacion.profesional_id == profesional_id,
            Autorizacion.activa.is_(True),
            (Autorizacion.fecha_expiracion.is_(None)) | (Autorizacion.fecha_expiracion > ahora_utc()),
            Nino.estado == 'activo',
            Nino.consentimiento_otorgado.is_(True),
            Evaluacion.nivel_riesgo == 'rojo',
        )
        .distinct()
        .all()
    )


def contar_alertas_rojas(profesional_id):
    return len(pacientes_en_rojo(profesional_id))
