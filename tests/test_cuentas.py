"""Cuentas: recuperación de contraseña, verificación de correo, sesiones ligadas a la contraseña y cierre de sesión."""
import hashlib
import re
from datetime import timedelta

from app import db, mail
from app.models import ahora_utc
from tests.conftest import PASSWORD, crear_cuidador, crear_profesional, login

NUEVA = 'NuevaClave2026'


def _enlace(mensaje, ruta):
    return re.search(rf'http://localhost(/auth/{ruta}/[\w-]+)', mensaje.body).group(1)


def _pedir_recuperacion(client, correo):
    with mail.record_messages() as buzon:
        respuesta = client.post('/auth/recuperar', data={'correo': correo})
    return respuesta, buzon


# ---------------------------------------------------------------- Recuperación de contraseña

def test_recuperacion_envia_enlace_de_un_solo_uso_guardado_como_hash(client, app):
    ana = crear_cuidador('ana@test.com')
    respuesta, buzon = _pedir_recuperacion(client, 'ana@test.com')
    assert respuesta.status_code == 302 and len(buzon) == 1
    assert buzon[0].recipients == ['ana@test.com'] and buzon[0].html
    ruta = _enlace(buzon[0], 'restablecer')
    token = ruta.rsplit('/', 1)[1]
    db.session.refresh(ana)
    # En la base solo queda el hash: quien lea la base no puede usar el enlace.
    assert ana.token_recuperacion == hashlib.sha256(token.encode()).hexdigest() != token
    assert client.get(ruta).status_code == 200


def test_no_revela_si_el_correo_existe(client, app):
    crear_cuidador('ana@test.com')
    existe, buzon_existe = _pedir_recuperacion(client, 'ana@test.com')
    mensaje_existe = client.get('/auth/login').get_data(as_text=True)
    no_existe, buzon_no_existe = _pedir_recuperacion(client, 'nadie@test.com')
    mensaje_no_existe = client.get('/auth/login').get_data(as_text=True)
    assert existe.status_code == no_existe.status_code == 302
    assert 'Si el correo corresponde' in mensaje_existe and 'Si el correo corresponde' in mensaje_no_existe
    assert len(buzon_existe) == 1 and len(buzon_no_existe) == 0


def test_restablecer_cambia_password_desbloquea_y_el_enlace_no_se_reutiliza(client, app):
    ana = crear_cuidador('ana@test.com')
    ana.bloqueado_hasta = ahora_utc() + timedelta(minutes=10)
    db.session.commit()
    _, buzon = _pedir_recuperacion(client, 'ana@test.com')
    ruta = _enlace(buzon[0], 'restablecer')

    respuesta = client.post(ruta, data={'password': NUEVA, 'password_confirmar': NUEVA})
    assert respuesta.status_code == 302 and respuesta.headers['Location'].endswith('/auth/login')
    db.session.refresh(ana)
    assert ana.check_password(NUEVA) and not ana.esta_bloqueado() and ana.token_recuperacion is None
    assert ana.correo_verificado  # usar el enlace demuestra el control del correo
    assert login(client, 'ana@test.com', PASSWORD).status_code == 401
    # El mismo enlace ya no sirve.
    assert client.post(ruta, data={'password': 'OtraClave99', 'password_confirmar': 'OtraClave99'}).status_code == 400


def test_restablecer_valida_la_politica_de_contrasena(client, app):
    crear_cuidador('ana@test.com')
    _, buzon = _pedir_recuperacion(client, 'ana@test.com')
    ruta = _enlace(buzon[0], 'restablecer')
    assert client.post(ruta, data={'password': 'corta', 'password_confirmar': 'corta'}).status_code == 400
    assert client.post(ruta, data={'password': NUEVA, 'password_confirmar': 'Distinta123'}).status_code == 400


def test_enlace_vencido_o_inventado_no_sirve(client, app):
    ana = crear_cuidador('ana@test.com')
    _, buzon = _pedir_recuperacion(client, 'ana@test.com')
    ruta = _enlace(buzon[0], 'restablecer')
    db.session.refresh(ana)
    ana.token_recuperacion_expira = ahora_utc() - timedelta(minutes=1)
    db.session.commit()
    assert client.get(ruta).status_code == 400
    assert 'no es válido' in client.get('/auth/restablecer/inventado').get_data(as_text=True)


def test_pedir_un_enlace_nuevo_invalida_el_anterior(client, app):
    crear_cuidador('ana@test.com')
    _, primero = _pedir_recuperacion(client, 'ana@test.com')
    _, segundo = _pedir_recuperacion(client, 'ana@test.com')
    assert client.get(_enlace(primero[0], 'restablecer')).status_code == 400
    assert client.get(_enlace(segundo[0], 'restablecer')).status_code == 200


def test_profesional_no_aprobado_no_recibe_enlace(client, app):
    crear_profesional('pendiente@test.com', estado='pendiente')
    crear_profesional('dra@test.com')
    assert len(_pedir_recuperacion(client, 'pendiente@test.com')[1]) == 0
    assert len(_pedir_recuperacion(client, 'dra@test.com')[1]) == 1


def test_restablecer_quita_la_contrasena_temporal_del_profesional(client, app):
    dra = crear_profesional('dra@test.com')
    dra.debe_cambiar_password = True
    db.session.commit()
    _, buzon = _pedir_recuperacion(client, 'dra@test.com')
    client.post(_enlace(buzon[0], 'restablecer'), data={'password': NUEVA, 'password_confirmar': NUEVA})
    db.session.refresh(dra)
    assert dra.debe_cambiar_password is False


# ---------------------------------------------------------------- Verificación de correo

def test_registro_envia_verificacion_y_el_enlace_confirma_el_correo(client, app):
    datos = {'nombre': 'Ana', 'apellido': 'Torres', 'correo': 'nueva@respirakids.co', 'telefono': '300 123 4567',
             'password': NUEVA, 'confirmar_password': NUEVA, 'acepta_politica': 'y',
             'acepta_terminos': 'y'}
    with mail.record_messages() as buzon:
        assert client.post('/auth/registro', data=datos).status_code == 302
    assert len(buzon) == 1 and buzon[0].recipients == ['nueva@respirakids.co']
    ruta = _enlace(buzon[0], 'verificar')

    from app.models import Cuidador
    cuidador = Cuidador.query.filter_by(correo='nueva@respirakids.co').one()
    assert cuidador.correo_verificado is False
    login(client, 'nueva@respirakids.co', NUEVA)
    assert 'Confirma tu correo' in client.get('/dashboard/cuidador').get_data(as_text=True)

    client.get(ruta)
    db.session.refresh(cuidador)
    assert cuidador.correo_verificado and cuidador.token_verificacion is None
    assert 'Confirma tu correo' not in client.get('/dashboard/cuidador').get_data(as_text=True)


def test_verificacion_con_enlace_invalido(client, app):
    respuesta = client.get('/auth/verificar/inventado', follow_redirects=True)
    assert 'no es válido' in respuesta.get_data(as_text=True)


def test_reenviar_verificacion(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    with mail.record_messages() as buzon:
        client.post('/auth/verificar/reenviar')
    assert len(buzon) == 1


# ---------------------------------------------------------------- Sesiones

def test_cambiar_password_cierra_las_demas_sesiones_y_conserva_la_actual(app):
    crear_cuidador('ana@test.com')
    telefono, robada = app.test_client(), app.test_client()
    # Cada cliente en su propio contexto: Flask-Login guarda el usuario de la petición en `g`.
    with app.app_context():
        login(telefono, 'ana@test.com')
    with app.app_context():
        login(robada, 'ana@test.com')
        assert robada.get('/dashboard/cuidador').status_code == 200
    with app.app_context():
        telefono.post('/dashboard/perfil', data={
            'accion': 'cambiar_password', 'password_actual': PASSWORD,
            'password_nueva': NUEVA, 'password_confirmar': NUEVA,
        })
        assert telefono.get('/dashboard/cuidador').status_code == 200
    with app.app_context():
        # La otra sesión (p. ej. un dispositivo robado) queda cerrada.
        assert robada.get('/dashboard/cuidador').status_code == 302


def test_logout_solo_por_post(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    # Un enlace o imagen de otro sitio (GET) no cierra la sesión: solo muestra la confirmación.
    assert 'Cerrar sesión?' in client.get('/auth/logout').get_data(as_text=True)
    assert client.get('/dashboard/cuidador').status_code == 200
    client.post('/auth/logout')
    assert client.get('/dashboard/cuidador').status_code == 302
