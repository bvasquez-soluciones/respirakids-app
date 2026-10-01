"""Base de conocimiento sanitario del asistente y registro de sus consultas."""
from app import db
from app.models.base import ahora_utc


class FuenteConocimiento(db.Model):
    __tablename__ = 'fuentes_conocimiento'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    tipo = db.Column(db.String(50))
    url = db.Column(db.String(500))
    fecha_publicacion = db.Column(db.Date)

    conocimientos = db.relationship('ConocimientoSanitario', back_populates='fuente', lazy=True)

    def __repr__(self):
        return f'<FuenteConocimiento {self.id}>'


class ConocimientoSanitario(db.Model):
    __tablename__ = 'conocimientos_sanitarios'

    id = db.Column(db.Integer, primary_key=True)
    fuente_id = db.Column(db.Integer, db.ForeignKey('fuentes_conocimiento.id'), nullable=False, index=True)
    categoria = db.Column(db.String(100), nullable=False)
    nivel = db.Column(db.String(50), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    contenido = db.Column(db.Text, nullable=False)
    tipo_contenido = db.Column(db.String(50))
    restricciones = db.Column(db.Text)
    edad_min_meses = db.Column(db.Integer)
    edad_max_meses = db.Column(db.Integer)
    fecha_actualizacion = db.Column(db.Date, nullable=False)
    activo = db.Column(db.Boolean, default=True)

    fuente = db.relationship('FuenteConocimiento', back_populates='conocimientos')

    def __repr__(self):
        return f'<ConocimientoSanitario {self.id} {self.categoria}>'


class ConsultaIA(db.Model):
    __tablename__ = 'consultas_ia'

    id = db.Column(db.Integer, primary_key=True)
    # Consulta al asistente. nino_id solo se llena cuando la pregunta es sobre una evaluación concreta.
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=True, index=True)
    cuidador_id = db.Column(db.Integer, db.ForeignKey('cuidadores.id'), nullable=False)
    categoria_sintoma = db.Column(db.String(50))
    contexto_json = db.Column(db.Text)
    resultado = db.Column(db.String(30))
    fuentes_citadas = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=ahora_utc)

    def __repr__(self):
        return f'<ConsultaIA {self.id}>'
