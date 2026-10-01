"""Usuarios del sistema: cuidadores (incluye administradores) y profesionales de salud."""
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from app.models.base import ahora_utc


class UsuarioMixin(UserMixin):
    """Comportamiento común de autenticación y bloqueo por intentos fallidos."""

    TIPO = None  # 'cuidador' o 'profesional'; forma parte del id de sesión

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f'{self.TIPO}-{self.id}'

    @property
    def tipo_usuario(self):
        return self.TIPO

    def esta_bloqueado(self):
        return self.bloqueado_hasta is not None and self.bloqueado_hasta > ahora_utc()

    @property
    def nombre_completo(self):
        return f'{self.nombre} {self.apellido}' if self.apellido else self.nombre


class Cuidador(UsuarioMixin, db.Model):
    __tablename__ = 'cuidadores'
    TIPO = 'cuidador'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100))
    correo = db.Column(db.String(120), unique=True, nullable=False)
    telefono = db.Column(db.String(30))
    tipo_documento = db.Column(db.String(20))
    numero_documento = db.Column(db.String(30))
    fecha_nacimiento = db.Column(db.Date)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='cuidador', server_default='cuidador')  # 'cuidador' o 'admin'
    fecha_registro = db.Column(db.DateTime, default=ahora_utc)

    # Seguridad de la cuenta
    intentos_fallidos = db.Column(db.Integer, default=0)
    bloqueado_hasta = db.Column(db.DateTime)
    correo_verificado = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())
    token_verificacion = db.Column(db.String(100))
    token_verificacion_expira = db.Column(db.DateTime)
    token_recuperacion = db.Column(db.String(100))
    token_recuperacion_expira = db.Column(db.DateTime)
    notificaciones_vistas_hasta = db.Column(db.DateTime)

    ninos = db.relationship('Nino', back_populates='cuidador', lazy=True)

    def __repr__(self):
        return f'<Cuidador {self.id} ({self.rol})>'


class Profesional(UsuarioMixin, db.Model):
    __tablename__ = 'profesionales'
    TIPO = 'profesional'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100))
    correo = db.Column(db.String(120), unique=True, nullable=False)
    telefono = db.Column(db.String(30))
    tipo_documento = db.Column(db.String(20))
    numero_documento = db.Column(db.String(30))
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='profesional')
    fecha_registro = db.Column(db.DateTime, default=ahora_utc)
    foto = db.Column(db.String(255))

    # Datos profesionales
    profesion = db.Column(db.String(100))
    especialidad = db.Column(db.String(100))
    numero_licencia = db.Column(db.String(50))
    tarjeta_profesional = db.Column(db.String(50))
    registro_rethus = db.Column(db.String(50))
    estado_aprobacion = db.Column(db.String(20), nullable=False, default='aprobado', server_default='aprobado')
    # Cuentas creadas por el administrador con contraseña temporal: deben cambiarla al ingresar.
    debe_cambiar_password = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false())

    # Seguridad de la cuenta
    intentos_fallidos = db.Column(db.Integer, default=0)
    bloqueado_hasta = db.Column(db.DateTime)
    token_recuperacion = db.Column(db.String(100))
    token_recuperacion_expira = db.Column(db.DateTime)
    notificaciones_vistas_hasta = db.Column(db.DateTime)

    autorizaciones = db.relationship('Autorizacion', back_populates='profesional', lazy=True)

    @property
    def aprobado(self):
        return self.estado_aprobacion == 'aprobado'

    def __repr__(self):
        return f'<Profesional {self.id}>'
