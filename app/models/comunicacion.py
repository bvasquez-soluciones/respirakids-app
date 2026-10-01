"""Mensajería entre cuidadores y profesionales, y notificaciones."""
from app import db
from app.models.base import ahora_utc


class Mensaje(db.Model):
    __tablename__ = 'mensajes'
    __table_args__ = (db.Index('ix_mensajes_nino_fecha', 'nino_id', 'fecha'),)

    id = db.Column(db.Integer, primary_key=True)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=False)
    # Profesional con quien se sostiene la conversación sobre el niño
    profesional_conversacion_id = db.Column(db.Integer, db.ForeignKey('profesionales.id'))

    autor_tipo = db.Column(db.String(20), nullable=False)  # 'cuidador' o 'profesional'
    autor_cuidador_id = db.Column(db.Integer, db.ForeignKey('cuidadores.id'))
    autor_profesional_id = db.Column(db.Integer, db.ForeignKey('profesionales.id'))

    contenido = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=ahora_utc)

    nino = db.relationship('Nino', back_populates='mensajes')
    autor_cuidador = db.relationship('Cuidador', foreign_keys=[autor_cuidador_id])
    autor_profesional = db.relationship('Profesional', foreign_keys=[autor_profesional_id])
    profesional_conversacion = db.relationship('Profesional', foreign_keys=[profesional_conversacion_id])

    def nombre_autor(self):
        if self.autor_tipo == 'cuidador' and self.autor_cuidador:
            return self.autor_cuidador.nombre
        if self.autor_tipo == 'profesional' and self.autor_profesional:
            return f'Dr(a). {self.autor_profesional.nombre}'
        return 'Usuario'

    def __repr__(self):
        return f'<Mensaje {self.id} nino={self.nino_id}>'


class Notificacion(db.Model):
    __tablename__ = 'notificaciones'
    __table_args__ = (db.Index('ix_notificaciones_usuario', 'usuario_tipo', 'usuario_id', 'leida'),)

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False)
    usuario_tipo = db.Column(db.String(20), nullable=False)
    tipo = db.Column(db.String(50), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    recurso = db.Column(db.String(50))
    recurso_id = db.Column(db.Integer)
    leida = db.Column(db.Boolean, nullable=False, default=False)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    fecha_lectura = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Notificacion {self.id} {self.usuario_tipo}-{self.usuario_id}>'
