from app import db
from app.models import Cuidador, LogSeguridad
from tests.conftest import PASSWORD, crear_cuidador, crear_profesional, login

DATOS_REGISTRO = {
    'nombre': 'Ana María', 'apellido': 'Torres Gómez', 'correo': 'Ana@Test.com', 'telefono': '300 123 4567',
    'password': PASSWORD, 'confirmar_password': PASSWORD, 'acepta_politica': 'y',
    'acepta_terminos': 'y',
}


def test_registro_valida_password_segura(client, app):
    datos = {**DATOS_REGISTRO, 'password': 'corta', 'confirmar_password': 'corta'}
    assert client.post('/auth/registro', data=datos).status_code == 400
    assert Cuidador.query.count() == 0

    assert client.post('/auth/registro', data=DATOS_REGISTRO).status_code == 302
    cuidador = Cuidador.query.one()
    assert (cuidador.nombre, cuidador.apellido, cuidador.correo) == ('Ana María', 'Torres Gómez', 'ana@test.com')


def test_registro_rechaza_correo_duplicado(client, app):
    crear_cuidador('ana@test.com')
    respuesta = client.post('/auth/registro', data=DATOS_REGISTRO)
    assert respuesta.status_code == 400
    assert 'Ya existe una cuenta con ese correo' in respuesta.get_data(as_text=True)
    assert Cuidador.query.count() == 1


def test_login_redirige_segun_rol(client, app):
    crear_cuidador('ana@test.com')
    crear_cuidador('admin@test.com', rol='admin')
    crear_profesional('dra@test.com')
    assert login(client, 'ana@test.com').headers['Location'].endswith('/dashboard/cuidador')
    client.post('/auth/logout')
    assert login(client, 'admin@test.com').headers['Location'].endswith('/admin/')
    client.post('/auth/logout')
    assert login(client, 'dra@test.com').headers['Location'].endswith('/dashboard/profesional')


def test_bloqueo_tras_intentos_fallidos(client, app):
    cuidador = crear_cuidador('ana@test.com')
    for _ in range(app.config['MAX_INTENTOS_LOGIN']):
        assert login(client, 'ana@test.com', 'incorrecta1').status_code == 401

    db.session.refresh(cuidador)
    assert cuidador.esta_bloqueado()
    # Con la cuenta bloqueada ni siquiera la contraseña correcta permite entrar.
    assert login(client, 'ana@test.com').status_code == 403
    assert LogSeguridad.query.filter_by(evento='cuenta_bloqueada').count() == 1


def test_login_exitoso_reinicia_intentos(client, app):
    cuidador = crear_cuidador('ana@test.com')
    login(client, 'ana@test.com', 'incorrecta1')
    assert login(client, 'ana@test.com').status_code == 302
    db.session.refresh(cuidador)
    assert cuidador.intentos_fallidos == 0
    assert LogSeguridad.query.filter_by(evento='login_exitoso').count() == 1


def test_profesional_no_aprobado_no_inicia_sesion(client, app):
    crear_profesional('dra@test.com', estado='pendiente')
    assert login(client, 'dra@test.com').status_code == 403


def test_redireccion_abierta_bloqueada(client, app):
    crear_cuidador('ana@test.com')
    respuesta = client.post('/auth/login?next=https://malicioso.com',
                            data={'correo': 'ana@test.com', 'password': PASSWORD})
    assert respuesta.headers['Location'].endswith('/dashboard/cuidador')


def test_redireccion_interna_permitida(client, app):
    crear_cuidador('ana@test.com')
    respuesta = client.post('/auth/login?next=/pacientes/', data={'correo': 'ana@test.com', 'password': PASSWORD})
    assert respuesta.headers['Location'].endswith('/pacientes/')


def test_login_acepta_cuentas_con_dominio_reservado(client, app):
    # Cuentas existentes (p. ej. las de seed_data.py en @respirakids.test) deben poder iniciar sesión.
    crear_profesional('dra.gomez@respirakids.test')
    assert login(client, 'dra.gomez@respirakids.test').status_code == 302
