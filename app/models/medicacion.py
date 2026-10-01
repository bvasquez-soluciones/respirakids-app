"""Indicaciones de medicamentos registradas por un profesional y su administración.

RespiraKids no genera recomendaciones farmacológicas: todo lo que hay aquí
lo indica un profesional de salud autorizado.
"""
from app import db
from app.models.base import ahora_utc


class Receta(db.Model):
    __tablename__ = 'recetas'

    id = db.Column(db.Integer, primary_key=True)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=False, index=True)
    profesional_id = db.Column(db.Integer, db.ForeignKey('profesionales.id'), nullable=False)
    motivo = db.Column(db.String(255))
    indicaciones_generales = db.Column(db.Text)
    fecha = db.Column(db.DateTime, default=ahora_utc)
    activa = db.Column(db.Boolean, default=True)

    nino = db.relationship('Nino', back_populates='recetas')
    profesional = db.relationship('Profesional')
    medicamentos = db.relationship('MedicamentoRecetado', back_populates='receta', lazy=True)

    def __repr__(self):
        return f'<Receta {self.id} nino={self.nino_id}>'


class MedicamentoRecetado(db.Model):
    __tablename__ = 'medicamentos_recetados'

    id = db.Column(db.Integer, primary_key=True)
    receta_id = db.Column(db.Integer, db.ForeignKey('recetas.id'), nullable=False, index=True)
    nombre = db.Column(db.String(150), nullable=False)
    dosis = db.Column(db.String(100), nullable=False)
    frecuencia_horas = db.Column(db.Integer, nullable=False)
    duracion_dias = db.Column(db.Integer)
    instrucciones = db.Column(db.Text)
    fecha_inicio = db.Column(db.DateTime, default=ahora_utc)
    activo = db.Column(db.Boolean, default=True)

    receta = db.relationship('Receta', back_populates='medicamentos')
    tomas = db.relationship('TomaMedicamento', back_populates='medicamento', lazy=True)

    def __repr__(self):
        return f'<MedicamentoRecetado {self.id} receta={self.receta_id}>'


class TomaMedicamento(db.Model):
    __tablename__ = 'tomas_medicamento'

    id = db.Column(db.Integer, primary_key=True)
    medicamento_id = db.Column(db.Integer, db.ForeignKey('medicamentos_recetados.id'), nullable=False, index=True)
    hora_programada = db.Column(db.DateTime, nullable=False)
    administrada = db.Column(db.Boolean, default=False)
    hora_administrada = db.Column(db.DateTime)
    administrado_por_id = db.Column(db.Integer, db.ForeignKey('cuidadores.id'))

    medicamento = db.relationship('MedicamentoRecetado', back_populates='tomas')
    administrado_por = db.relationship('Cuidador')

    def __repr__(self):
        return f'<TomaMedicamento {self.id} medicamento={self.medicamento_id}>'
