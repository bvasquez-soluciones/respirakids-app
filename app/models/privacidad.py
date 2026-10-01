"""Consentimientos y solicitudes de derechos del titular (Ley 1581 de 2012)."""
from app import db
from app.models.base import ahora_utc

# Tipos de consentimiento
POLITICA_DATOS = 'politica_datos'              # usuario acepta la política de tratamiento de datos
TRATAMIENTO_NINO = 'tratamiento_datos_nino'    # representante autoriza el tratamiento de datos de salud del niño
INVESTIGACION_NINO = 'investigacion_nino'      # uso anonimizado para investigación y mejora (opcional)

TIPOS_SOLICITUD = {
    'consulta': 'Consultar qué datos tiene RespiraKids',
    'rectificacion': 'Actualizar o rectificar datos',
    'supresion': 'Suprimir mis datos o los de un niño/a',
    'revocatoria': 'Revocar la autorización de tratamiento',
    'queja': 'Otra petición, queja o reclamo',
}
ESTADOS_SOLICITUD = ('pendiente', 'en_tramite', 'resuelta', 'rechazada')


class Consentimiento(db.Model):
    """Historial inmutable de autorizaciones otorgadas o revocadas (cada cambio es una fila nueva)."""
    __tablename__ = 'consentimientos'
    __table_args__ = (
        db.Index('ix_consentimientos_usuario', 'usuario_tipo', 'usuario_id', 'tipo'),
        db.Index('ix_consentimientos_nino', 'nino_id', 'tipo'),
    )

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False)
    usuario_tipo = db.Column(db.String(20), nullable=False)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'))
    tipo = db.Column(db.String(40), nullable=False)
    version_politica = db.Column(db.String(20), nullable=False)
    otorgado = db.Column(db.Boolean, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    ip = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))

    def __repr__(self):
        return f'<Consentimiento {self.tipo} {self.usuario_tipo}-{self.usuario_id} {self.otorgado}>'


class SolicitudDerechos(db.Model):
    """Petición del titular para ejercer sus derechos sobre los datos personales."""
    __tablename__ = 'solicitudes_derechos'
    __table_args__ = (db.Index('ix_solicitudes_derechos_usuario', 'usuario_tipo', 'usuario_id'),)

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False)
    usuario_tipo = db.Column(db.String(20), nullable=False)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'))
    tipo = db.Column(db.String(30), nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='pendiente', server_default='pendiente')
    respuesta = db.Column(db.Text)
    fecha_solicitud = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    fecha_respuesta = db.Column(db.DateTime)

    nino = db.relationship('Nino')

    @property
    def tipo_texto(self):
        return TIPOS_SOLICITUD.get(self.tipo, self.tipo)

    def __repr__(self):
        return f'<SolicitudDerechos {self.id} {self.tipo} {self.estado}>'
