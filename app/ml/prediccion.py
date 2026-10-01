"""Predicción complementaria: nunca modifica la clasificación clínica por reglas.

El modelo solo se carga si su hash SHA-256 coincide con el registrado en sus metadatos (joblib usa pickle,
que puede ejecutar código: no se carga un archivo alterado).
"""
import json
import os
from dataclasses import asdict, dataclass

import joblib
import pandas as pd
from flask import current_app

from app.clinica.motor import DatosEvaluacion
from app.ml.entrenamiento import matriz_variables, ruta_metadatos, sha256_archivo


@dataclass
class PrediccionML:
    nivel: str
    confianza: float          # probabilidad de la clase predicha, en %
    version: str


_cache = {'clave': None, 'modelo': None, 'metadatos': None}


def metadatos_modelo():
    """Metadatos (ficha) del modelo configurado, o None si no existe."""
    ruta = ruta_metadatos(current_app.config['ML_RUTA_MODELO'])
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding='utf-8') as archivo:
        return json.load(archivo)


def _cargar():
    ruta = current_app.config['ML_RUTA_MODELO']
    if not os.path.exists(ruta):
        return None, None
    clave = (ruta, os.path.getmtime(ruta))
    if _cache['clave'] == clave:
        return _cache['modelo'], _cache['metadatos']

    metadatos = metadatos_modelo()
    if not metadatos or metadatos.get('sha256_modelo') != sha256_archivo(ruta):
        current_app.logger.error('Modelo ML descartado: falta su ficha o el hash no coincide (%s)', ruta)
        return None, None
    modelo = joblib.load(ruta)
    _cache.update(clave=clave, modelo=modelo, metadatos=metadatos)
    return modelo, metadatos


def predecir(registro, nino):
    """Predicción complementaria para un registro, o None si el ML está apagado, no disponible o falla."""
    if not current_app.config.get('ML_HABILITADO'):
        return None
    try:
        modelo, metadatos = _cargar()
        if modelo is None:
            return None
        datos = asdict(DatosEvaluacion.desde_registro(registro, nino))
        x = matriz_variables(pd.DataFrame([datos]))[metadatos['variables']]
        probabilidades = modelo.predict_proba(x)[0]
        indice = int(probabilidades.argmax())
        return PrediccionML(nivel=str(modelo.classes_[indice]), confianza=round(float(probabilidades[indice]) * 100, 1),
                            version=metadatos['version'])
    except Exception:
        current_app.logger.exception('Fallo en la predicción ML complementaria')
        return None


def concordancia_con_reglas():
    """Seguimiento agregado: cuántas predicciones ML coinciden con la clasificación por reglas, por versión."""
    from app.models import Evaluacion
    resumen = {}
    for e in Evaluacion.query.filter(Evaluacion.ml_nivel_riesgo.isnot(None)).all():
        fila = resumen.setdefault(e.ml_version or 'anterior', {'total': 0, 'coinciden': 0, 'rojo_no_detectado': 0})
        fila['total'] += 1
        fila['coinciden'] += int(not e.discrepancia_ml)
        fila['rojo_no_detectado'] += int(e.nivel_riesgo == 'rojo' and e.ml_nivel != 'rojo')
    for fila in resumen.values():
        fila['porcentaje'] = round(100 * fila['coinciden'] / fila['total']) if fila['total'] else None
    return resumen
