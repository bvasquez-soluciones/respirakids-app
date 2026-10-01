"""Control de acceso a la información de los niños.

Toda ruta que reciba un id de niño (u objeto dependiente de un niño) debe obtenerlo
a través de estas funciones. Si el usuario no tiene permiso se responde 404, para
no revelar si el registro existe.
"""
from flask import abort
from flask_login import current_user

from app import db
from app.models import Autorizacion, Nino, ahora_utc
from app.services.auditoria import registrar_seguridad


def es_cuidador(usuario=None):
    usuario = usuario or current_user
    return usuario.is_authenticated and usuario.tipo_usuario == 'cuidador'


def es_profesional(usuario=None):
    usuario = usuario or current_user
    return usuario.is_authenticated and usuario.tipo_usuario == 'profesional'


def _denegar(nino_id):
    registrar_seguridad('acceso_denegado', descripcion=f'nino_id={nino_id}')
    abort(404)


def autorizacion_vigente(nino_id, profesional_id):
    ahora = ahora_utc()
    return (
        Autorizacion.query
        .filter(
            Autorizacion.nino_id == nino_id,
            Autorizacion.profesional_id == profesional_id,
            Autorizacion.activa.is_(True),
            (Autorizacion.fecha_expiracion.is_(None)) | (Autorizacion.fecha_expiracion > ahora),
        )
        .first()
    )


def autorizaciones_vigentes_profesional(profesional_id):
    """Autorizaciones vigentes de un profesional sobre niños activos."""
    ahora = ahora_utc()
    return (
        Autorizacion.query
        .join(Nino, Nino.id == Autorizacion.nino_id)
        .filter(
            Autorizacion.profesional_id == profesional_id,
            Autorizacion.activa.is_(True),
            (Autorizacion.fecha_expiracion.is_(None)) | (Autorizacion.fecha_expiracion > ahora),
            Nino.estado == 'activo',
            Nino.consentimiento_otorgado.is_(True),
        )
        .all()
    )


def autorizaciones_vigentes_nino(nino_id):
    """Autorizaciones vigentes de profesionales sobre un niño."""
    ahora = ahora_utc()
    return (
        Autorizacion.query
        .filter(
            Autorizacion.nino_id == nino_id,
            Autorizacion.activa.is_(True),
            (Autorizacion.fecha_expiracion.is_(None)) | (Autorizacion.fecha_expiracion > ahora),
        )
        .all()
    )


def nino_del_cuidador(nino_id, solo_activos=False):
    """Niño que pertenece al cuidador autenticado."""
    nino = db.session.get(Nino, nino_id)
    if nino is None or not es_cuidador() or nino.cuidador_id != current_user.id:
        _denegar(nino_id)
    if solo_activos and not nino.activo:
        abort(404)
    return nino


def nino_del_profesional(nino_id):
    """Niño activo, con tratamiento de datos autorizado, sobre el que el profesional tiene autorización vigente."""
    nino = db.session.get(Nino, nino_id)
    if (nino is None or not nino.activo or not nino.consentimiento_otorgado
            or not es_profesional() or not autorizacion_vigente(nino_id, current_user.id)):
        _denegar(nino_id)
    return nino


def nino_accesible(nino_id):
    """Niño visible para el usuario actual, sea su cuidador o un profesional autorizado."""
    if es_profesional():
        return nino_del_profesional(nino_id)
    return nino_del_cuidador(nino_id)
