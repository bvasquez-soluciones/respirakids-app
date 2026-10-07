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
    adjuntos = db.relationship('AdjuntoMensaje', back_populates='mensaje', lazy=True, order_by='AdjuntoMensaje.id')

    def nombre_autor(self):
        if self.autor_tipo == 'cuidador' and self.autor_cuidador:
            return self.autor_cuidador.nombre
        if self.autor_tipo == 'profesional' and self.autor_profesional:
            return self.autor_profesional.nombre_con_titulo
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


class SolicitudAtencion(db.Model):
    """Petición del cuidador para hablar con un profesional de la clínica ("Conectando con un profesional...").

    La ven todos los profesionales disponibles con cupo; el primero que la acepta atiende el caso y se abre su
    conversación privada con el cuidador. Después el cuidador decide si le autoriza el acceso al expediente
    completo del niño/a (`acceso`). El caso lo cierra el profesional.
    """
    __tablename__ = 'solicitudes_atencion'
    __table_args__ = (
        db.CheckConstraint("estado IN ('pendiente', 'asignada', 'cerrada', 'cancelada')",
                           name='ck_solicitudes_atencion_estado'),
        db.CheckConstraint("acceso IS NULL OR acceso IN ('otorgado', 'denegado')", name='ck_solicitudes_atencion_acceso'),
    )

    id = db.Column(db.Integer, primary_key=True)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=False, index=True)
    cuidador_id = db.Column(db.Integer, db.ForeignKey('cuidadores.id'), index=True)  # vacío si se anonimizó
    profesional_id = db.Column(db.Integer, db.ForeignKey('profesionales.id'), index=True)
    evaluacion_id = db.Column(db.Integer, db.ForeignKey('evaluaciones.id'))
    motivo = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(15), nullable=False, default='pendiente', server_default='pendiente', index=True)
    acceso = db.Column(db.String(10))  # None = sin responder, 'otorgado' o 'denegado'
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    fecha_asignacion = db.Column(db.DateTime)
    fecha_cierre = db.Column(db.DateTime)

    nino = db.relationship('Nino')
    profesional = db.relationship('Profesional')
    evaluacion = db.relationship('Evaluacion')

    @property
    def abierta(self):
        return self.estado in ('pendiente', 'asignada')

    def __repr__(self):
        return f'<SolicitudAtencion {self.id} nino={self.nino_id} {self.estado}>'


class AdjuntoMensaje(db.Model):
    """Imagen, documento PDF o nota de voz adjunta a un mensaje.

    El archivo vive en una carpeta PRIVADA (ADJUNTOS_FOLDER, fuera de /static) y solo se entrega por
    /mensajes/adjunto/<id> a quien puede ver esa conversación. Ver services/adjuntos.py.
    """
    __tablename__ = 'adjuntos_mensaje'
    __table_args__ = (
        db.CheckConstraint("tipo IN ('imagen', 'documento', 'audio')", name='ck_adjuntos_mensaje_tipo'),
    )

    id = db.Column(db.Integer, primary_key=True)
    mensaje_id = db.Column(db.Integer, db.ForeignKey('mensajes.id'), nullable=False, index=True)
    tipo = db.Column(db.String(10), nullable=False)
    mime = db.Column(db.String(60), nullable=False)
    archivo = db.Column(db.String(80), nullable=False, unique=True)  # nombre aleatorio en disco
    nombre_original = db.Column(db.String(150), nullable=False)
    tamano = db.Column(db.Integer, nullable=False)  # bytes
    fecha = db.Column(db.DateTime, nullable=False, default=ahora_utc)

    mensaje = db.relationship('Mensaje', back_populates='adjuntos')

    def __repr__(self):
        return f'<AdjuntoMensaje {self.id} {self.tipo}>'


class Videollamada(db.Model):
    """Atención por video entre un profesional y el cuidador de un niño/a que atiende (telemedicina).

    La inicia solo el profesional, con un paciente que atiende: caso abierto o autorización vigente del cuidador.
    El video viaja directamente entre los dos
    dispositivos (WebRTC, cifrado) y NO se graba: aquí solo queda el registro de quién, cuándo, cuánto duró y el
    consentimiento del cuidador. Ver services/videollamadas.py.
    """
    __tablename__ = 'videollamadas'
    ESTADOS_ACTIVOS = ('llamando', 'en_curso')
    __table_args__ = (
        db.CheckConstraint("estado IN ('llamando', 'en_curso', 'finalizada', 'rechazada', 'perdida', 'cancelada')",
                           name='ck_videollamadas_estado'),
    )

    id = db.Column(db.Integer, primary_key=True)
    # Caso de atención en el que se hizo la llamada (vacío si el profesional atiende por autorización del cuidador).
    solicitud_id = db.Column(db.Integer, db.ForeignKey('solicitudes_atencion.id'), index=True)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=False, index=True)
    profesional_id = db.Column(db.Integer, db.ForeignKey('profesionales.id'), nullable=False, index=True)
    cuidador_id = db.Column(db.Integer, db.ForeignKey('cuidadores.id'), index=True)  # vacío si se anonimizó
    estado = db.Column(db.String(12), nullable=False, default='llamando', server_default='llamando', index=True)
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=ahora_utc)
    fecha_respuesta = db.Column(db.DateTime)
    fecha_fin = db.Column(db.DateTime)
    consentimiento_fecha = db.Column(db.DateTime)  # el cuidador aceptó la atención por video
    # Última señal de vida de cada lado (para detectar una desconexión sin colgar).
    pulso_profesional = db.Column(db.DateTime)
    pulso_cuidador = db.Column(db.DateTime)

    nino = db.relationship('Nino')
    profesional = db.relationship('Profesional')
    solicitud = db.relationship('SolicitudAtencion')

    @property
    def activa(self):
        return self.estado in self.ESTADOS_ACTIVOS

    @property
    def duracion_segundos(self):
        if self.fecha_respuesta and self.fecha_fin:
            return max(0, int((self.fecha_fin - self.fecha_respuesta).total_seconds()))
        return 0

    def __repr__(self):
        return f'<Videollamada {self.id} nino={self.nino_id} {self.estado}>'


class SenalVideollamada(db.Model):
    """Mensaje técnico para conectar los dos dispositivos (oferta, respuesta y candidatos de red de WebRTC).

    Es temporal: contiene direcciones de red, así que se borra en cuanto termina la llamada.
    """
    __tablename__ = 'senales_videollamada'
    __table_args__ = (
        db.CheckConstraint("emisor IN ('profesional', 'cuidador')", name='ck_senales_videollamada_emisor'),
        db.CheckConstraint("tipo IN ('oferta', 'respuesta', 'candidato')", name='ck_senales_videollamada_tipo'),
    )

    id = db.Column(db.Integer, primary_key=True)
    videollamada_id = db.Column(db.Integer, db.ForeignKey('videollamadas.id'), nullable=False, index=True)
    emisor = db.Column(db.String(12), nullable=False)
    tipo = db.Column(db.String(10), nullable=False)
    datos = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=ahora_utc)
