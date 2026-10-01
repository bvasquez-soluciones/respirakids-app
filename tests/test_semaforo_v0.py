"""Pruebas de caracterización de las reglas PROVISIONALES actuales (semaforo.py).

Documentan el comportamiento vigente para que cualquier cambio en la lógica clínica
sea deliberado y visible. Se reemplazarán cuando se implemente el motor clínico v1.
"""
from app.models import RegistroSintomas
from app.semaforo import clasificar_riesgo

CAMPOS_BOOLEANOS = (
    'tos', 'dificultad_respiratoria', 'respiracion_rapida', 'congestion_nasal', 'secrecion_nasal',
    'dolor_garganta', 'decaimiento', 'perdida_apetito', 'vomito', 'diarrea', 'estornudos', 'irritabilidad',
)


def registro(**campos):
    base = {c: False for c in CAMPOS_BOOLEANOS}
    base.update(temperatura=None, severidad=None, inicio_sintomas=None)
    base.update(campos)
    return RegistroSintomas(**base)


def test_sin_sintomas_es_verde():
    assert clasificar_riesgo(registro())[0] == 'verde'


def test_tos_sola_es_amarillo():
    assert clasificar_riesgo(registro(tos=True))[0] == 'amarillo'


def test_dificultad_respiratoria_es_rojo():
    assert clasificar_riesgo(registro(dificultad_respiratoria=True))[0] == 'rojo'


def test_umbrales_de_temperatura():
    assert clasificar_riesgo(registro(temperatura=37.9))[0] == 'verde'
    assert clasificar_riesgo(registro(temperatura=38.0))[0] == 'amarillo'
    assert clasificar_riesgo(registro(temperatura=39.0))[0] == 'rojo'


def test_umbrales_de_severidad():
    assert clasificar_riesgo(registro(severidad=4))[0] == 'verde'
    assert clasificar_riesgo(registro(severidad=5))[0] == 'amarillo'
    assert clasificar_riesgo(registro(severidad=8))[0] == 'rojo'
