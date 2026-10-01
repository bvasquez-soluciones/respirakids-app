"""Registro de eventos de seguridad y de actividad sobre información clínica.

Los fallos al auditar se registran en el log de la aplicación pero no interrumpen
la operación del usuario.
"""
import json

from flask import current_app, has_request_context, request
from flask_login import current_user

from app import db
from app.models import LogActividad, LogSeguridad


def _contexto_peticion():
    if not has_request_context():
        return None, None
    return request.remote_addr, (request.user_agent.string or '')[:500]


def _usuario_actual():
    if has_request_context() and current_user and current_user.is_authenticated:
        return current_user.id, current_user.tipo_usuario
    return None, None


def _guardar(registro):
    try:
        db.session.add(registro)
        db.session.commit()
    except Exception:  # la auditoría nunca debe tumbar la petición
        db.session.rollback()
        current_app.logger.exception('No se pudo guardar el registro de auditoría')


def registrar_seguridad(evento, usuario=None, descripcion=None):
    """Eventos de autenticación y control de acceso (login, bloqueo, acceso denegado...)."""
    ip, user_agent = _contexto_peticion()
    if usuario is not None:
        usuario_id, usuario_tipo = usuario.id, usuario.tipo_usuario
    else:
        usuario_id, usuario_tipo = _usuario_actual()
    current_app.logger.info('seguridad evento=%s usuario=%s-%s ip=%s', evento, usuario_tipo, usuario_id, ip)
    _guardar(LogSeguridad(
        usuario_id=usuario_id, usuario_tipo=usuario_tipo, evento=evento,
        descripcion=descripcion, ip=ip, user_agent=user_agent,
    ))


def registrar_actividad(accion, recurso=None, recurso_id=None, detalles=None, resultado='ok'):
    """Acciones sobre información de niños (consultar, crear, modificar, compartir...)."""
    ip, user_agent = _contexto_peticion()
    usuario_id, usuario_tipo = _usuario_actual()
    if isinstance(detalles, dict):
        detalles = json.dumps(detalles, ensure_ascii=False, default=str)
    _guardar(LogActividad(
        usuario_id=usuario_id, usuario_tipo=usuario_tipo, accion=accion,
        recurso=recurso, recurso_id=recurso_id, detalles=detalles,
        resultado=resultado, ip=ip, user_agent=user_agent,
    ))
