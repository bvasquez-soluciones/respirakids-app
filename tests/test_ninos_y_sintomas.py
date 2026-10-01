from datetime import date, timedelta

from app import db
from app.models import Evaluacion, Nino, RegistroSintomas
from tests.conftest import crear_cuidador, crear_nino, login


def _datos_nino(**cambios):
    datos = {
        'nombre': 'Sofía', 'apellido': 'Torres', 'sexo': 'F',
        'fecha_nacimiento': (date.today() - timedelta(days=400)).isoformat(),
        'consentimiento_tratamiento': 'y',
    }
    datos.update(cambios)
    return datos


def test_registrar_nino(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    assert client.post('/pacientes/nuevo', data=_datos_nino()).status_code == 302
    nino = Nino.query.one()
    assert nino.nombre == 'Sofía' and nino.estado == 'activo'


def test_registrar_nino_valida_fechas_y_edad(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    futura = (date.today() + timedelta(days=1)).isoformat()
    mayor = (date.today() - timedelta(days=6 * 365)).isoformat()
    assert client.post('/pacientes/nuevo', data=_datos_nino(fecha_nacimiento=futura)).status_code == 400
    assert client.post('/pacientes/nuevo', data=_datos_nino(fecha_nacimiento=mayor)).status_code == 400
    assert client.post('/pacientes/nuevo', data=_datos_nino(fecha_nacimiento='')).status_code == 400
    assert Nino.query.count() == 0


def test_registro_de_sintomas_crea_evaluacion(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    respuesta = client.post(f'/sintomas/nino/{nino.id}/nuevo', data={'tos': 'on', 'temperatura': '38.4'})
    assert respuesta.status_code == 302

    registro = RegistroSintomas.query.one()
    evaluacion = Evaluacion.query.one()
    assert registro.tos is True and registro.temperatura == 38.4
    assert evaluacion.registro_sintomas_id == registro.id
    assert evaluacion.nivel_riesgo in ('verde', 'amarillo', 'rojo')
    assert evaluacion.ml_nivel_riesgo is None  # ML apagado en pruebas
    assert client.get(respuesta.headers['Location']).status_code == 200


def test_registro_de_sintomas_valida_datos(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    for datos in ({'temperatura': '50'}, {'temperatura': 'abc'}, {'dias_fiebre': '-1'}, {'tos_paroxistica': 'y'}):
        assert client.post(f'/sintomas/nino/{nino.id}/nuevo', data=datos).status_code == 400
    assert RegistroSintomas.query.count() == 0 and Evaluacion.query.count() == 0


def test_no_se_registran_sintomas_de_nino_inactivo(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'), estado='inactivo')
    login(client, 'ana@test.com')
    assert client.post(f'/sintomas/nino/{nino.id}/nuevo', data={'tos': 'on'}).status_code == 404


def test_desactivar_y_reactivar_nino(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    client.post(f'/pacientes/{nino.id}/eliminar')
    assert db.session.get(Nino, nino.id).estado == 'inactivo'
    client.post(f'/pacientes/{nino.id}/reactivar')
    assert db.session.get(Nino, nino.id).estado == 'activo'


def test_edad_en_meses():
    nino = Nino(fecha_nacimiento=date(2024, 3, 15))
    assert nino.edad_meses(date(2024, 4, 14)) == 0
    assert nino.edad_meses(date(2024, 4, 15)) == 1
    assert nino.edad_meses(date(2026, 3, 15)) == 24
