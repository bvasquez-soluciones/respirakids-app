"""Trazabilidad: eventos de seguridad, actividad sobre recursos y versiones de registros."""
from app import db
from app.models.base import ahora_utc


class LogSeguridad(db.Model):
    __tablename__ = 'logs_seguridad'
    __table_args__ = (db.Index('ix_logs_seguridad_usuario', 'usuario_tipo', 'usuario_id'),)

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer)
    usuario_tipo = db.Column(db.String(20))
    evento = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.Text)
    ip = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, nullable=False, default=ahora_utc)


class LogActividad(db.Model):
    __tablename__ = 'logs_actividad'
    __table_args__ = (
        db.Index('ix_logs_actividad_usuario', 'usuario_tipo', 'usuario_id'),
        db.Index('ix_logs_actividad_recurso', 'recurso', 'recurso_id'),
    )

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer)
    usuario_tipo = db.Column(db.String(20))
    accion = db.Column(db.String(50), nullable=False)
    recurso = db.Column(db.String(50))
    recurso_id = db.Column(db.Integer)
    detalles = db.Column(db.Text)
    resultado = db.Column(db.String(20))
    ip = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, nullable=False, default=ahora_utc)


class VersionRegistro(db.Model):
    __tablename__ = 'versiones_registro'
    __table_args__ = (db.Index('ix_versiones_registro_tabla_registro', 'tabla', 'registro_id'),)

    id = db.Column(db.Integer, primary_key=True)
    tabla = db.Column(db.String(50), nullable=False)
    registro_id = db.Column(db.Integer, nullable=False)
    version = db.Column(db.Integer, nullable=False)
    accion = db.Column(db.String(20), nullable=False)
    datos = db.Column(db.Text, nullable=False)  # JSON con el estado del registro
    usuario_id = db.Column(db.Integer)
    usuario_tipo = db.Column(db.String(20))
    timestamp = db.Column(db.DateTime, nullable=False, default=ahora_utc)
