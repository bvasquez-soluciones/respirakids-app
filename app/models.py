from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class Cuidador(db.Model, UserMixin):
    __tablename__ = 'cuidadores'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    telefono = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), default='cuidador', nullable=False)  # 'cuidador' o 'admin'
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    ninos = db.relationship('Nino', backref='cuidador', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f'cuidador-{self.id}'

    def __repr__(self):
        return f'<Cuidador {self.nombre} ({self.rol})>'


class Profesional(db.Model, UserMixin):
    __tablename__ = 'profesionales'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    especialidad = db.Column(db.String(100), nullable=True)
    numero_licencia = db.Column(db.String(50), nullable=True)
    foto = db.Column(db.String(255), nullable=True)
    rol = db.Column(db.String(20), default='profesional', nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        return f'profesional-{self.id}'

    def __repr__(self):
        return f'<Profesional {self.nombre}>'


class Nino(db.Model):
    __tablename__ = 'ninos'

    id = db.Column(db.Integer, primary_key=True)
    nombre_ficticio = db.Column(db.String(100), nullable=False)
    fecha_nacimiento = db.Column(db.Date, nullable=False)
    sexo = db.Column(db.String(1), nullable=False)
    estado = db.Column(db.String(20), default='activo')
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    cuidador_id = db.Column(db.Integer, db.ForeignKey('cuidadores.id'), nullable=False)

    def __repr__(self):
        return f'<Nino {self.nombre_ficticio}>'

    def edad_texto(self):
        from datetime import date
        hoy = date.today()
        años = hoy.year - self.fecha_nacimiento.year
        meses = hoy.month - self.fecha_nacimiento.month
        if hoy.day < self.fecha_nacimiento.day:
            meses -= 1
        if meses < 0:
            años -= 1
            meses += 12
        if meses == 0:
            return f"{años} años"
        return f"{años} años, {meses} meses"

    def ultima_actualizacion_texto(self):
        ultimo = None
        if self.evaluaciones:
            ultimo = sorted(self.evaluaciones, key=lambda e: e.fecha)[-1].fecha
        elif self.registros_sintomas:
            ultimo = sorted(self.registros_sintomas, key=lambda r: r.fecha)[-1].fecha
        
        if not ultimo:
            return None
            
        from datetime import datetime
        diff = datetime.utcnow() - ultimo
        minutos = int(diff.total_seconds() // 60)
        
        if minutos < 1:
            return "Ahora mismo"
        if minutos < 60:
            return f"Hace {minutos}m"
        horas = minutos // 60
        if horas < 24:
            return f"Hace {horas}h"
        dias = horas // 24
        return f"Hace {dias}d"


class RegistroSintomas(db.Model):
    __tablename__ = 'registros_sintomas'

    id = db.Column(db.Integer, primary_key=True)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    temperatura = db.Column(db.Float, nullable=True)
    tos = db.Column(db.Boolean, default=False)
    dificultad_respiratoria = db.Column(db.Boolean, default=False)
    respiracion_rapida = db.Column(db.Boolean, default=False)
    congestion_nasal = db.Column(db.Boolean, default=False)
    secrecion_nasal = db.Column(db.Boolean, default=False)
    dolor_garganta = db.Column(db.Boolean, default=False)
    decaimiento = db.Column(db.Boolean, default=False)
    perdida_apetito = db.Column(db.Boolean, default=False)
    vomito = db.Column(db.Boolean, default=False)
    diarrea = db.Column(db.Boolean, default=False)
    otros_sintomas = db.Column(db.Text, nullable=True)
    observaciones = db.Column(db.Text, nullable=True)

    severidad = db.Column(db.Integer, nullable=True)  # 1 a 10
    inicio_sintomas = db.Column(db.String(20), nullable=True)  # 'hoy', 'ayer', '2_3_dias', 'mas_3_dias'
    estornudos = db.Column(db.Boolean, default=False)
    irritabilidad = db.Column(db.Boolean, default=False)
    condicion_asma = db.Column(db.Boolean, default=False)
    condicion_alergias = db.Column(db.Boolean, default=False)

    nino = db.relationship('Nino', backref='registros_sintomas')

    def __repr__(self):
        return f'<RegistroSintomas Nino#{self.nino_id} {self.fecha}>'


class Evaluacion(db.Model):
    __tablename__ = 'evaluaciones'

    id = db.Column(db.Integer, primary_key=True)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=False)
    registro_sintomas_id = db.Column(db.Integer, db.ForeignKey('registros_sintomas.id'), nullable=False)
    nivel_riesgo = db.Column(db.String(10), nullable=False)  # 'verde', 'amarillo', 'rojo'
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    motivo = db.Column(db.Text, nullable=True)
    recomendaciones = db.Column(db.Text, nullable=True)

    # Campos de Machine Learning
    ml_nivel_riesgo = db.Column(db.String(10), nullable=True)
    ml_confianza = db.Column(db.Float, nullable=True)

    nino = db.relationship('Nino', backref='evaluaciones')
    registro_sintomas = db.relationship('RegistroSintomas', backref=db.backref('evaluacion', uselist=False))

    def __repr__(self):
        return f'<Evaluacion Nino#{self.nino_id} {self.nivel_riesgo}>'


class Autorizacion(db.Model):
    __tablename__ = 'autorizaciones'

    id = db.Column(db.Integer, primary_key=True)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=False)
    profesional_id = db.Column(db.Integer, db.ForeignKey('profesionales.id'), nullable=False)
    fecha_autorizacion = db.Column(db.DateTime, default=datetime.utcnow)
    activa = db.Column(db.Boolean, default=True)

    nino = db.relationship('Nino', backref='autorizaciones')
    profesional = db.relationship('Profesional', backref='autorizaciones')

    def __repr__(self):
        return f'<Autorizacion Nino#{self.nino_id} -> Profesional#{self.profesional_id}>'


class Mensaje(db.Model):
    __tablename__ = 'mensajes'

    id = db.Column(db.Integer, primary_key=True)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=False)

    autor_tipo = db.Column(db.String(20), nullable=False)  # 'cuidador' o 'profesional'
    autor_cuidador_id = db.Column(db.Integer, db.ForeignKey('cuidadores.id'), nullable=True)
    autor_profesional_id = db.Column(db.Integer, db.ForeignKey('profesionales.id'), nullable=True)

    contenido = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    nino = db.relationship('Nino', backref='mensajes')
    autor_cuidador = db.relationship('Cuidador')
    autor_profesional = db.relationship('Profesional')

    def nombre_autor(self):
        if self.autor_tipo == 'cuidador' and self.autor_cuidador:
            return self.autor_cuidador.nombre
        elif self.autor_tipo == 'profesional' and self.autor_profesional:
            return f'Dr(a). {self.autor_profesional.nombre}'
        return 'Usuario'

    def __repr__(self):
        return f'<Mensaje Nino#{self.nino_id} por {self.autor_tipo}>'


class PatologiaBase(db.Model):
    __tablename__ = 'patologias_base'

    id = db.Column(db.Integer, primary_key=True)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=False)

    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    fecha_diagnostico = db.Column(db.Date, nullable=True)
    activa = db.Column(db.Boolean, default=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    nino = db.relationship('Nino', backref='patologias_base')

    def __repr__(self):
        return f'<PatologiaBase {self.nombre} - Nino#{self.nino_id}>'