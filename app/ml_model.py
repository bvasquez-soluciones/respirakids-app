"""
Módulo de Machine Learning - RespiraKids

⚠️ Este modelo fue entrenado con datos SINTÉTICOS (ficticios) generados
para fines académicos. NO ha sido validado clínicamente. Sus resultados
son complementarios a las reglas de clasificación definidas en semaforo.py
y NUNCA deben usarse como única base para decisiones de salud reales.
"""
import os
import joblib

_RUTA_MODELO = os.path.join('app', 'ml_models', 'riesgo_model.pkl')
_modelo_data = None
NIVELES = {0: 'verde', 1: 'amarillo', 2: 'rojo'}

MAPA_INICIO = {'hoy': 0, 'ayer': 1, '2_3_dias': 2, 'mas_3_dias': 3}


def _cargar_modelo():
    global _modelo_data
    if _modelo_data is None and os.path.exists(_RUTA_MODELO):
        _modelo_data = joblib.load(_RUTA_MODELO)
    return _modelo_data


def predecir_riesgo_ml(registro, nino):
    """
    Recibe un RegistroSintomas y su Nino asociado.
    Devuelve (nivel_riesgo_str, confianza_float) o (None, None) si el modelo no está disponible.
    """
    data = _cargar_modelo()
    if data is None:
        return None, None

    modelo = data['modelo']
    features = data['features']

    hoy_dias = (registro.fecha.date() - nino.fecha_nacimiento).days
    edad_meses = max(hoy_dias // 30, 0)

    num_patologias_base = len([p for p in nino.patologias_base if p.activa])
    num_episodios_previos = len(nino.registros_sintomas) - 1  # excluye el actual

    fila = {
        'edad_meses': edad_meses,
        'temperatura': registro.temperatura if registro.temperatura is not None else 37.0,
        'severidad': registro.severidad if registro.severidad is not None else 1,
        'dias_inicio': MAPA_INICIO.get(registro.inicio_sintomas, 0),
        'tos': int(registro.tos),
        'dificultad_respiratoria': int(registro.dificultad_respiratoria),
        'respiracion_rapida': int(registro.respiracion_rapida),
        'congestion_nasal': int(registro.congestion_nasal),
        'secrecion_nasal': int(registro.secrecion_nasal),
        'dolor_garganta': int(registro.dolor_garganta),
        'decaimiento': int(registro.decaimiento),
        'perdida_apetito': int(registro.perdida_apetito),
        'vomito': int(registro.vomito),
        'diarrea': int(registro.diarrea),
        'estornudos': int(registro.estornudos),
        'irritabilidad': int(registro.irritabilidad),
        'condicion_asma': int(registro.condicion_asma),
        'condicion_alergias': int(registro.condicion_alergias),
        'num_patologias_base': num_patologias_base,
        'num_episodios_previos': max(num_episodios_previos, 0),
    }

    X = [[fila[f] for f in features]]
    prediccion = modelo.predict(X)[0]
    probabilidades = modelo.predict_proba(X)[0]
    confianza = float(max(probabilidades))

    return NIVELES[prediccion], round(confianza * 100, 1)