"""ML complementario: dataset sintético, entrenamiento trazable, integridad y separación de las reglas."""
import json
import os

import pytest

from app.clinica.motor import DatosEvaluacion, evaluar_v1
from app.ml import prediccion
from app.ml.entrenamiento import (
    VARIABLES, entrenar, ficha_markdown, generar_dataset, guardar, ruta_metadatos, sha256_archivo,
)
from app.ml.prediccion import PrediccionML, metadatos_modelo, predecir
from app.models import Evaluacion
from tests.conftest import autorizar, crear_cuidador, crear_nino, crear_profesional, login


@pytest.fixture(scope='module')
def dataset():
    return generar_dataset(filas=900, semilla=7)


@pytest.fixture
def modelo_entrenado(app, dataset, tmp_path):
    ruta = str(tmp_path / 'modelo.joblib')
    modelo, metadatos = entrenar(dataset, semilla=7, arboles=25)
    guardar(modelo, metadatos, ruta)
    app.config.update(ML_HABILITADO=True, ML_RUTA_MODELO=ruta)
    prediccion._cache['clave'] = None
    return ruta


# ---------------------------------------------------------------- Dataset sintético

def test_dataset_usa_las_variables_del_motor_y_menores_de_5_anios(dataset):
    assert list(dataset.columns[:len(VARIABLES)]) == list(VARIABLES)
    assert dataset['edad_meses'].between(0, 59).all()
    assert set(dataset['nivel']) == {'verde', 'amarillo', 'rojo'}


def test_etiquetas_del_dataset_son_las_de_las_reglas(dataset):
    for _, fila in dataset.head(150).iterrows():
        datos = {v: (None if fila[v] != fila[v] else fila[v]) for v in VARIABLES}   # NaN -> None
        for v in ('edad_meses', 'frecuencia_respiratoria', 'altitud_msnm', 'dias_tos', 'dias_fiebre'):
            datos[v] = int(datos[v]) if datos[v] is not None else None
        assert evaluar_v1(DatosEvaluacion(**datos)).nivel == fila['nivel']


def test_dataset_es_reproducible():
    assert generar_dataset(filas=50, semilla=3).equals(generar_dataset(filas=50, semilla=3))


# ---------------------------------------------------------------- Entrenamiento y ficha

def test_metadatos_y_ficha_del_modelo(app, modelo_entrenado):
    with open(ruta_metadatos(modelo_entrenado), encoding='utf-8') as archivo:
        m = json.load(archivo)
    assert m['version'] == 'ml-v1-sintetico' and m['dataset']['tipo'] == 'SINTÉTICO'
    assert m['variables'] == list(VARIABLES) and m['fecha_entrenamiento']
    assert m['sha256_modelo'] == sha256_archivo(modelo_entrenado)
    assert {'exactitud', 'f1_macro', 'sensibilidad_por_clase', 'rojos_predichos_como_verde'} <= set(m['metricas_prueba'])
    ficha = ficha_markdown(m)
    assert 'SINTÉTICOS' in ficha and 'No tiene validación clínica' in ficha and 'Limitaciones' in ficha


def test_modelo_del_repositorio_coincide_con_su_ficha():
    ruta = os.path.join('app', 'ml_models', 'riesgo_v1.joblib')
    with open(ruta_metadatos(ruta), encoding='utf-8') as archivo:
        assert json.load(archivo)['sha256_modelo'] == sha256_archivo(ruta)
    with open(os.path.join('ml', 'MODELO_ML.md'), encoding='utf-8') as archivo:
        assert 'ml-v1-sintetico' in archivo.read()


# ---------------------------------------------------------------- Predicción

def test_prediccion_devuelve_nivel_confianza_y_version(app, modelo_entrenado):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    from app.models import RegistroSintomas, ahora_utc
    registro = RegistroSintomas(nino_id=nino.id, fecha=ahora_utc(), cianosis=True, tos=True)
    resultado = predecir(registro, nino)
    assert isinstance(resultado, PrediccionML)
    assert resultado.nivel in ('verde', 'amarillo', 'rojo') and 0 < resultado.confianza <= 100
    assert resultado.version == 'ml-v1-sintetico'
    assert metadatos_modelo()['version'] == 'ml-v1-sintetico'


def test_modelo_alterado_no_se_carga(app, modelo_entrenado):
    with open(modelo_entrenado, 'ab') as archivo:
        archivo.write(b'alterado')
    nino = crear_nino(crear_cuidador('ana@test.com'))
    from app.models import RegistroSintomas, ahora_utc
    assert predecir(RegistroSintomas(nino_id=nino.id, fecha=ahora_utc(), tos=True), nino) is None


def test_ml_desactivado_no_predice(app):
    app.config['ML_HABILITADO'] = False
    nino = crear_nino(crear_cuidador('ana@test.com'))
    from app.models import RegistroSintomas, ahora_utc
    assert predecir(RegistroSintomas(nino_id=nino.id, fecha=ahora_utc(), tos=True), nino) is None


# ---------------------------------------------------------------- Separación de las reglas

def test_el_ml_nunca_cambia_la_clasificacion_ni_se_muestra_al_cuidador(client, app, monkeypatch):
    # Se fuerza una predicción contraria a las reglas: la clasificación válida debe seguir siendo la de las reglas.
    monkeypatch.setattr('app.sintomas.routes.predecir',
                        lambda registro, nino: PrediccionML(nivel='verde', confianza=99.0, version='ml-prueba'))
    cuidador = crear_cuidador('ana@test.com')
    nino = crear_nino(cuidador)
    autorizar(nino, crear_profesional('dra@test.com'))
    login(client, 'ana@test.com')
    destino = client.post(f'/sintomas/nino/{nino.id}/nuevo', data={'cianosis': 'y'}).headers['Location']

    evaluacion = Evaluacion.query.one()
    assert evaluacion.nivel_riesgo == 'rojo'                       # decide la regla R02, no el ML
    assert evaluacion.ml_nivel == 'verde' and evaluacion.ml_version == 'ml-prueba' and evaluacion.discrepancia_ml
    html = client.get(destino).get_data(as_text=True)
    assert 'Machine Learning' not in html and 'ml-prueba' not in html
    client.get('/auth/logout')

    login(client, 'dra@test.com')
    detalle = client.get(f'/dashboard/profesional/evaluacion/{evaluacion.id}').get_data(as_text=True)
    assert 'ml-prueba' in detalle and 'No coincide con las reglas' in detalle
    assert 'ML difiere' in client.get(f'/dashboard/profesional?paciente={nino.id}').get_data(as_text=True)


@pytest.mark.parametrize('correo,rol,codigo', [
    ('dra@test.com', 'profesional', 200), ('admin@test.com', 'admin', 200), ('ana@test.com', 'cuidador', 403)])
def test_acceso_a_la_ficha_del_modelo(client, app, correo, rol, codigo):
    if rol == 'profesional':
        crear_profesional(correo)
    else:
        crear_cuidador(correo, rol=rol)
    login(client, correo)
    respuesta = client.get('/dashboard/modelo-ml')
    assert respuesta.status_code == codigo
    if codigo == 200:
        assert 'SINTÉTICOS' in respuesta.get_data(as_text=True)
