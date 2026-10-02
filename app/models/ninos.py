"""Ficha del niño, sus condiciones de base, las autorizaciones de acceso a profesionales y el seguimiento
de evolución que reporta el cuidador."""
from datetime import date

from app import db
from app.models.base import ahora_utc


class Nino(db.Model):
    __tablename__ = 'ninos'

    id = db.Column(db.Integer, primary_key=True)
    # Vacío solo en registros anonimizados (supresión): quedan desvinculados de cualquier persona.
    cuidador_id = db.Column(db.Integer, db.ForeignKey('cuidadores.id'), index=True)

    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100))
    tipo_documento = db.Column(db.String(20))
    numero_documento = db.Column(db.String(30))
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    sexo = db.Column(db.String(1), nullable=False)  # 'M' o 'F'
    peso_kg = db.Column(db.Float)
    talla_cm = db.Column(db.Float)
    estado = db.Column(db.String(20), default='activo')  # 'activo', 'inactivo' o 'anonimizado' (supresión)
    fecha_registro = db.Column(db.DateTime, default=ahora_utc)

    # Consentimiento del representante legal
    consentimiento_otorgado = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    consentimiento_fecha = db.Column(db.DateTime)
    consentimiento_ip = db.Column(db.String(45))
    consentimiento_investigacion_otorgado = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    consentimiento_investigacion_fecha = db.Column(db.DateTime)
    consentimiento_investigacion_ip = db.Column(db.String(45))

    # OBSOLETO: alias usado en la etapa de prototipo. La aplicación usa `nombre`.
    # Se conserva solo para no perder datos; no debe leerse ni mostrarse.
    nombre_ficticio = db.Column(db.String(100), nullable=False, server_default='Sin nombre')

    cuidador = db.relationship('Cuidador', back_populates='ninos')
    registros_sintomas = db.relationship('RegistroSintomas', back_populates='nino', lazy=True)
    evaluaciones = db.relationship('Evaluacion', back_populates='nino', lazy=True)
    autorizaciones = db.relationship('Autorizacion', back_populates='nino', lazy=True)
    mensajes = db.relationship('Mensaje', back_populates='nino', lazy=True)
    patologias_base = db.relationship('PatologiaBase', back_populates='nino', lazy=True)
    recetas = db.relationship('Receta', back_populates='nino', lazy=True)
    seguimientos = db.relationship('SeguimientoEvolucion', back_populates='nino', lazy=True,
                                   order_by='SeguimientoEvolucion.fecha')

    def __repr__(self):
        return f'<Nino {self.id}>'

    @property
    def nombre_completo(self):
        return f'{self.nombre} {self.apellido}' if self.apellido else self.nombre

    @property
    def activo(self):
        return self.estado == 'activo'

    def edad_meses(self, en_fecha=None):
        """Edad cumplida en meses a la fecha indicada (hoy por defecto)."""
        en_fecha = en_fecha or date.today()
        meses = (en_fecha.year - self.fecha_nacimiento.year) * 12 + (en_fecha.month - self.fecha_nacimiento.month)
        if en_fecha.day < self.fecha_nacimiento.day:
            meses -= 1
        return max(meses, 0)

    def edad_texto(self):
        meses = self.edad_meses()
        if meses < 1:
            dias = (date.today() - self.fecha_nacimiento).days
            return f'{dias} día{"s" if dias != 1 else ""}'
        if meses < 24:
            return f'{meses} mes{"es" if meses != 1 else ""}'
        anios, resto = divmod(meses, 12)
        texto = f'{anios} años'
        return f'{texto}, {resto} mes{"es" if resto != 1 else ""}' if resto else texto

    def ultima_evaluacion(self):
        return max(self.evaluaciones, key=lambda e: e.fecha, default=None)

    def ultima_actualizacion_texto(self):
        fechas = [e.fecha for e in self.evaluaciones] or [r.fecha for r in self.registros_sintomas]
        if not fechas:
            return None
        minutos = int((ahora_utc() - max(fechas)).total_seconds() // 60)
        if minutos < 1:
            return 'Ahora mismo'
        if minutos < 60:
            return f'Hace {minutos}m'
        horas = minutos // 60
        if horas < 24:
            return f'Hace {horas}h'
        return f'Hace {horas // 24}d'


class PatologiaBase(db.Model):
    __tablename__ = 'patologias_base'

    id = db.Column(db.Integer, primary_key=True)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=False, index=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    fecha_diagnostico = db.Column(db.Date)
    activa = db.Column(db.Boolean, default=True)
    fecha_registro = db.Column(db.DateTime, default=ahora_utc)

    nino = db.relationship('Nino', back_populates='patologias_base')

    def __repr__(self):
        return f'<PatologiaBase {self.id} nino={self.nino_id}>'


class Autorizacion(db.Model):
    """Permiso que un cuidador otorga a un profesional para ver la información de un niño."""
    __tablename__ = 'autorizaciones'
    __table_args__ = (db.Index('ix_autorizaciones_nino_profesional', 'nino_id', 'profesional_id'),)

    id = db.Column(db.Integer, primary_key=True)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=False)
    profesional_id = db.Column(db.Integer, db.ForeignKey('profesionales.id'), nullable=False, index=True)
    fecha_autorizacion = db.Column(db.DateTime, default=ahora_utc)
    fecha_expiracion = db.Column(db.DateTime)
    activa = db.Column(db.Boolean, default=True)

    nino = db.relationship('Nino', back_populates='autorizaciones')
    profesional = db.relationship('Profesional', back_populates='autorizaciones')

    @property
    def vigente(self):
        return bool(self.activa) and (self.fecha_expiracion is None or self.fecha_expiracion > ahora_utc())

    def __repr__(self):
        return f'<Autorizacion nino={self.nino_id} profesional={self.profesional_id}>'


class SeguimientoEvolucion(db.Model):
    """Cómo percibe el cuidador la evolución del niño/a desde su última evaluación (mejoró, sigue igual, empeoró).

    Es información de seguimiento reportada por el cuidador: NO es una evaluación clínica, no se envía al motor
    de reglas y nunca cambia la clasificación AIEPI. Si el cuidador indica que empeoró, la aplicación le sugiere
    registrar los síntomas de nuevo para obtener una orientación actualizada con el motor existente.
    """
    __tablename__ = 'seguimientos_evolucion'
    __table_args__ = (
        db.CheckConstraint("estado IN ('mejoro', 'igual', 'empeoro')", name='ck_seguimientos_evolucion_estado'),
    )
    ESTADOS = ('mejoro', 'igual', 'empeoro')

    id = db.Column(db.Integer, primary_key=True)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=False, index=True)
    cuidador_id = db.Column(db.Integer, db.ForeignKey('cuidadores.id'), index=True)  # vacío si se anonimizó
    # Evaluación de referencia ("desde la última evaluación"); se conserva aunque luego haya otras.
    evaluacion_id = db.Column(db.Integer, db.ForeignKey('evaluaciones.id'), index=True)
    estado = db.Column(db.String(10), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=ahora_utc, index=True)

    nino = db.relationship('Nino', back_populates='seguimientos')
    evaluacion = db.relationship('Evaluacion')

    def __repr__(self):
        return f'<SeguimientoEvolucion nino={self.nino_id} {self.estado}>'
