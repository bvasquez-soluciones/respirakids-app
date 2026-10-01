"""Un usuario nunca debe acceder a información de niños que no le corresponden."""
from datetime import timedelta

import pytest

from app import db
from app.models import Autorizacion, LogSeguridad, PatologiaBase, ahora_utc
from tests.conftest import (
    autorizar, crear_cuidador, crear_nino, crear_patologia, crear_profesional, login,
)


@pytest.fixture
def escenario(app):
    ana = crear_cuidador('ana@test.com')
    luis = crear_cuidador('luis@test.com')
    nino_ana = crear_nino(ana, 'Sofía')
    nino_luis = crear_nino(luis, 'Mateo')
    dra = crear_profesional('dra@test.com')
    return {'ana': ana, 'luis': luis, 'nino_ana': nino_ana, 'nino_luis': nino_luis, 'dra': dra}


@pytest.mark.parametrize('metodo,ruta', [
    ('get', '/sintomas/nino/{id}'),
    ('get', '/sintomas/nino/{id}/nuevo'),
    ('get', '/pacientes/{id}/editar'),
    ('get', '/pacientes/{id}/autorizaciones'),
    ('get', '/pacientes/{id}/patologias'),
    ('get', '/mensajes/nino/{id}'),
    ('post', '/pacientes/{id}/eliminar'),
    ('post', '/pacientes/{id}/reactivar'),
])
def test_cuidador_no_accede_a_ninos_ajenos(client, escenario, metodo, ruta):
    login(client, 'luis@test.com')
    respuesta = getattr(client, metodo)(ruta.format(id=escenario['nino_ana'].id))
    assert respuesta.status_code == 404


def test_cuidador_ve_sus_propios_ninos(client, escenario):
    login(client, 'ana@test.com')
    assert client.get(f'/sintomas/nino/{escenario["nino_ana"].id}').status_code == 200
    assert client.get(f'/pacientes/{escenario["nino_ana"].id}/editar').status_code == 200


def test_no_se_puede_revocar_autorizacion_de_otro_nino(client, escenario):
    autorizacion_ana = autorizar(escenario['nino_ana'], escenario['dra'])
    login(client, 'luis@test.com')
    # Luis usa el id de SU niño, pero la autorización pertenece al niño de Ana.
    respuesta = client.post(
        f'/pacientes/{escenario["nino_luis"].id}/autorizaciones/{autorizacion_ana.id}/revocar'
    )
    assert respuesta.status_code == 404
    assert db.session.get(Autorizacion, autorizacion_ana.id).activa is True


def test_no_se_puede_eliminar_patologia_de_otro_nino(client, escenario):
    patologia_ana = crear_patologia(escenario['nino_ana'])
    login(client, 'luis@test.com')
    respuesta = client.post(
        f'/pacientes/{escenario["nino_luis"].id}/patologias/{patologia_ana.id}/eliminar'
    )
    assert respuesta.status_code == 404
    assert db.session.get(PatologiaBase, patologia_ana.id).activa is True


def test_cuidador_no_ve_resultado_de_evaluacion_ajena(client, escenario):
    login(client, 'ana@test.com')
    client.post(f'/sintomas/nino/{escenario["nino_ana"].id}/nuevo', data={'tos': 'on'})
    client.get('/auth/logout')

    login(client, 'luis@test.com')
    assert client.get('/sintomas/resultado/1').status_code == 404


def test_profesional_sin_autorizacion_no_ve_paciente(client, escenario):
    login(client, 'dra@test.com')
    assert client.get(f'/dashboard/profesional?paciente={escenario["nino_ana"].id}').status_code == 404
    assert client.get(f'/mensajes/nino/{escenario["nino_ana"].id}').status_code == 404


def test_profesional_autorizado_ve_paciente(client, escenario):
    autorizar(escenario['nino_ana'], escenario['dra'])
    login(client, 'dra@test.com')
    assert client.get(f'/dashboard/profesional?paciente={escenario["nino_ana"].id}').status_code == 200
    assert client.get(f'/mensajes/nino/{escenario["nino_ana"].id}').status_code == 200


def test_autorizacion_revocada_o_expirada_no_da_acceso(client, escenario):
    autorizar(escenario['nino_ana'], escenario['dra'], fecha_expiracion=ahora_utc() - timedelta(days=1))
    otra = autorizar(escenario['nino_luis'], escenario['dra'])
    otra.activa = False
    db.session.commit()

    login(client, 'dra@test.com')
    assert client.get(f'/dashboard/profesional?paciente={escenario["nino_ana"].id}').status_code == 404
    assert client.get(f'/dashboard/profesional?paciente={escenario["nino_luis"].id}').status_code == 404


def test_profesional_no_usa_rutas_de_cuidador(client, escenario):
    login(client, 'dra@test.com')
    assert client.get('/pacientes/').status_code == 403
    assert client.get('/dashboard/cuidador').status_code == 403


def test_cuidador_no_usa_rutas_de_profesional_ni_admin(client, escenario):
    login(client, 'ana@test.com')
    assert client.get('/dashboard/profesional').status_code == 403
    assert client.get('/dashboard/reportes').status_code == 403
    assert client.get('/dashboard/admin').status_code == 403


def test_acceso_denegado_queda_auditado(client, escenario):
    login(client, 'luis@test.com')
    client.get(f'/sintomas/nino/{escenario["nino_ana"].id}')
    assert LogSeguridad.query.filter_by(evento='acceso_denegado').count() == 1


def test_rutas_protegidas_exigen_sesion(client, escenario):
    for ruta in ('/dashboard/cuidador', '/pacientes/', '/asistente/', f'/mensajes/nino/{escenario["nino_ana"].id}'):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 302
        assert '/auth/login' in respuesta.headers['Location']
