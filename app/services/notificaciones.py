"""Notificaciones dentro de la aplicación."""
from app import db
from app.models import Notificacion, ahora_utc


def notificar(usuario_id, usuario_tipo, tipo, titulo, contenido, recurso=None, recurso_id=None):
    db.session.add(Notificacion(
        usuario_id=usuario_id, usuario_tipo=usuario_tipo, tipo=tipo, titulo=titulo,
        contenido=contenido, recurso=recurso, recurso_id=recurso_id, leida=False,
    ))


def _del_usuario(usuario):
    return Notificacion.query.filter_by(usuario_id=usuario.id, usuario_tipo=usuario.tipo_usuario)


def contar_no_leidas(usuario):
    return _del_usuario(usuario).filter(Notificacion.leida.is_(False)).count()


def recientes(usuario, limite=50):
    return _del_usuario(usuario).order_by(Notificacion.fecha_creacion.desc()).limit(limite).all()


def marcar_todas_leidas(usuario):
    _del_usuario(usuario).filter(Notificacion.leida.is_(False)).update(
        {Notificacion.leida: True, Notificacion.fecha_lectura: ahora_utc()}, synchronize_session=False)
    db.session.commit()
