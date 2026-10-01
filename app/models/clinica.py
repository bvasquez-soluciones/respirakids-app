"""Registros de síntomas y evaluaciones de riesgo."""
import json

from app import db
from app.models.base import ahora_utc

NIVELES_RIESGO = ('verde', 'amarillo', 'rojo')

# Algunas predicciones antiguas del modelo ML se guardaron como índice numérico.
_ML_NIVEL_LEGADO = {'0': 'verde', '1': 'amarillo', '2': 'rojo'}


class RegistroSintomas(db.Model):
    __tablename__ = 'registros_sintomas'
    __table_args__ = (db.Index('ix_registros_sintomas_nino_fecha', 'nino_id', 'fecha'),)

    id = db.Column(db.Integer, primary_key=True)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=False)
    fecha = db.Column(db.DateTime, default=ahora_utc)
    tipo = db.Column(db.String(20), nullable=False, default='sintomas', server_default='sintomas')
    estado_evolucion = db.Column(db.String(20))

    # Síntomas reportados por el cuidador
    temperatura = db.Column(db.Float)
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
    estornudos = db.Column(db.Boolean, default=False)
    irritabilidad = db.Column(db.Boolean, default=False)
    otros_sintomas = db.Column(db.Text)
    observaciones = db.Column(db.Text)

    severidad = db.Column(db.Integer)  # 1 a 10, percepción del cuidador
    inicio_sintomas = db.Column(db.String(20))  # 'hoy', 'ayer', '2_3_dias', 'mas_3_dias'
    dias_sintomas = db.Column(db.Integer)

    # Antecedentes declarados en el registro
    condicion_asma = db.Column(db.Boolean, default=False)
    condicion_alergias = db.Column(db.Boolean, default=False)

    # Signos clínicos (Herramienta Clínica Primera Infancia, Módulo 6)
    frecuencia_respiratoria = db.Column(db.Integer)
    frecuencia_cardiaca = db.Column(db.Integer)
    spo2 = db.Column(db.Float)
    tiraje_subcostal = db.Column(db.Boolean, default=False, server_default=db.false())
    cianosis = db.Column(db.Boolean, default=False, server_default=db.false())
    incapacidad_beber_liquidos = db.Column(db.Boolean, default=False, server_default=db.false())
    aleteo_nasal = db.Column(db.Boolean, default=False)
    quejido = db.Column(db.Boolean, default=False)
    estridor = db.Column(db.Boolean, default=False)
    uso_musculos_accesorios = db.Column(db.Boolean, default=False)
    apnea = db.Column(db.Boolean, default=False)
    convulsion = db.Column(db.Boolean, default=False)
    palidez_extrema = db.Column(db.Boolean, default=False)
    alteracion_conciencia = db.Column(db.Boolean, default=False)

    # Datos adicionales requeridos por los criterios de la Herramienta Clínica (motor v1)
    sibilancias = db.Column(db.Boolean, default=False)
    tos_paroxistica = db.Column(db.Boolean, default=False)          # accesos de tos
    vomito_tras_tos = db.Column(db.Boolean, default=False)          # vómitos por acceso de tos
    dias_tos = db.Column(db.Integer)
    dias_fiebre = db.Column(db.Integer)
    contacto_tuberculosis = db.Column(db.Boolean, default=False)
    perdida_peso = db.Column(db.Boolean, default=False)             # pérdida o no ganancia de peso
    disminucion_actividad = db.Column(db.Boolean, default=False)    # disminución de la actividad o juego
    rigidez_cuello = db.Column(db.Boolean, default=False)
    abombamiento_fontanela = db.Column(db.Boolean, default=False)
    petequias = db.Column(db.Boolean, default=False)                # púrpura / petequias
    edema_retroauricular = db.Column(db.Boolean, default=False)     # edema y eritema detrás de la oreja
    factor_riesgo_bar = db.Column(db.Boolean, default=False)        # factores de bronquiolitis de alto riesgo
    altitud_msnm = db.Column(db.Integer)                            # para interpretar la saturación de oxígeno

    nino = db.relationship('Nino', back_populates='registros_sintomas')
    evaluacion = db.relationship('Evaluacion', back_populates='registro_sintomas', uselist=False)

    def __repr__(self):
        return f'<RegistroSintomas {self.id} nino={self.nino_id}>'


class Evaluacion(db.Model):
    __tablename__ = 'evaluaciones'
    __table_args__ = (db.Index('ix_evaluaciones_nino_fecha', 'nino_id', 'fecha'),)

    id = db.Column(db.Integer, primary_key=True)
    nino_id = db.Column(db.Integer, db.ForeignKey('ninos.id'), nullable=False)
    registro_sintomas_id = db.Column(db.Integer, db.ForeignKey('registros_sintomas.id'), nullable=False, index=True)
    fecha = db.Column(db.DateTime, default=ahora_utc)

    # Clasificación clínica por reglas (determinante)
    nivel_riesgo = db.Column(db.String(10), nullable=False)  # 'verde', 'amarillo', 'rojo'
    motivo = db.Column(db.Text)
    recomendaciones = db.Column(db.Text)

    # Trazabilidad: versión del conjunto de reglas y señales identificadas (JSON) en el momento de evaluar.
    # NULL en evaluaciones antiguas = reglas v0 provisionales.
    version_reglas = db.Column(db.String(30))
    senales_json = db.Column(db.Text)

    # Predicción complementaria del modelo ML (nunca modifica nivel_riesgo)
    ml_nivel_riesgo = db.Column(db.String(10))
    ml_confianza = db.Column(db.Float)
    ml_version = db.Column(db.String(30))

    nino = db.relationship('Nino', back_populates='evaluaciones')
    registro_sintomas = db.relationship('RegistroSintomas', back_populates='evaluacion')

    @property
    def version_reglas_efectiva(self):
        return self.version_reglas or 'v0-provisional'

    @property
    def detalle(self):
        """Señales y avisos guardados al evaluar, o None si la evaluación es anterior a v1."""
        return json.loads(self.senales_json) if self.senales_json else None

    @property
    def discrepancia_ml(self):
        """True si la predicción complementaria no coincide con la clasificación por reglas."""
        return self.ml_nivel is not None and self.ml_nivel != self.nivel_riesgo

    @property
    def ml_nivel(self):
        """Nivel ML normalizado ('verde'/'amarillo'/'rojo') o None."""
        if self.ml_nivel_riesgo is None:
            return None
        return _ML_NIVEL_LEGADO.get(self.ml_nivel_riesgo, self.ml_nivel_riesgo)

    def __repr__(self):
        return f'<Evaluacion {self.id} nino={self.nino_id} {self.nivel_riesgo}>'
