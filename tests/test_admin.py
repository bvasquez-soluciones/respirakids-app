"""Panel de administración: acceso, profesionales, cuentas, solicitudes de derechos, auditoría y catálogos."""
import re
from datetime import date

import pytest

from app import db
from app.asistente.conocimiento import importar_documento
from app.models import (
    ConocimientoSanitario, Cuidador, LogActividad, Notificacion, Profesional, SolicitudDerechos, ahora_utc,
)
from app.services.plazos import fecha_limite, sumar_dias_habiles
from tests.conftest import PASSWORD, aceptar_politica, crear_cuidador, crear_nino, crear_profesional, login

PAGINAS = ('/admin/', '/admin/profesionales', '/admin/profesionales/nuevo', '/admin/cuidadores',
           '/admin/solicitudes', '/admin/auditoria', '/admin/auditoria?tipo=actividad', '/admin/conocimiento',
           '/admin/reglas', '/admin/modelo-ml', '/admin/configuracion')

DATOS_PROFESIONAL = {
    'nombre': 'Laura', 'apellido': 'Gómez', 'correo': 'laura@clinica.co', 'telefono': '3001234567',
    'tipo_documento': 'CC', 'numero_documento': '52123456', 'profesion': 'Medicina',
    'especialidad': 'Pediatría', 'tarjeta_profesional': 'TP-123',
}


@pytest.fixture
def admin(client, app):
    crear_cuidador('admin@test.com', rol='admin')
    login(client, 'admin@test.com')


# ---------------------------------------------------------------- Acceso

@pytest.mark.parametrize('correo,crear', [('ana@test.com', 'cuidador'), ('dra@test.com', 'profesional')])
def test_solo_el_administrador_accede(client, app, correo, crear):
    (crear_cuidador if crear == 'cuidador' else crear_profesional)(correo)
    login(client, correo)
    for ruta in PAGINAS:
        assert client.get(ruta).status_code == 403, ruta


def test_sin_sesion_redirige_al_login(client, app):
    assert '/auth/login' in client.get('/admin/').headers['Location']


def test_todas_las_paginas_renderizan(client, admin):
    for ruta in PAGINAS:
        assert client.get(ruta).status_code == 200, ruta


def test_resumen_no_expone_datos_clinicos_individuales(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'), 'Valentina')
    crear_cuidador('admin@test.com', rol='admin')
    login(client, 'ana@test.com')
    client.post(f'/sintomas/nino/{nino.id}/nuevo', data={'tiraje_subcostal': 'y'})
    client.get('/auth/logout')
    login(client, 'admin@test.com')
    for ruta in ('/admin/', '/admin/cuidadores'):
        assert 'Valentina' not in client.get(ruta).get_data(as_text=True)


# ---------------------------------------------------------------- Profesionales

def test_alta_de_profesional_con_contrasena_temporal(client, admin):
    respuesta = client.post('/admin/profesionales/nuevo', data=DATOS_PROFESIONAL)
    assert respuesta.status_code == 200 and respuesta.headers['Cache-Control'] == 'no-store'
    clave = re.search(r'<code class="fs-5" id="clave">([^<]+)</code>', respuesta.get_data(as_text=True)).group(1)

    profesional = Profesional.query.filter_by(correo='laura@clinica.co').one()
    assert profesional.estado_aprobacion == 'pendiente' and profesional.debe_cambiar_password
    assert profesional.check_password(clave) and clave not in profesional.password_hash
    assert LogActividad.query.filter_by(accion='crear_profesional').count() == 1


def test_alta_de_profesional_valida_campos_y_correo_unico(client, admin):
    respuesta = client.post('/admin/profesionales/nuevo', data={**DATOS_PROFESIONAL, 'tarjeta_profesional': ''})
    assert respuesta.status_code == 400 and 'id="tarjeta_profesional-error"' in respuesta.get_data(as_text=True)
    respuesta = client.post('/admin/profesionales/nuevo', data={**DATOS_PROFESIONAL, 'correo': 'admin@test.com'})
    assert 'Ya existe una cuenta con ese correo' in respuesta.get_data(as_text=True)
    assert Profesional.query.count() == 0


def test_flujo_aprobacion_y_cambio_obligatorio_de_contrasena(client, admin):
    html = client.post('/admin/profesionales/nuevo', data=DATOS_PROFESIONAL).get_data(as_text=True)
    clave = re.search(r'id="clave">([^<]+)<', html).group(1)
    profesional = Profesional.query.one()
    client.get('/auth/logout')

    assert login(client, 'laura@clinica.co', clave).status_code == 403          # pendiente de aprobación

    login(client, 'admin@test.com')
    client.post(f'/admin/profesionales/{profesional.id}/estado', data={'estado': 'aprobado'})
    client.get('/auth/logout')

    login(client, 'laura@clinica.co', clave)
    aceptar_politica(profesional)
    assert client.get('/dashboard/profesional').headers['Location'].endswith('/dashboard/ajustes')
    client.post('/dashboard/ajustes', data={'accion': 'cambiar_password', 'password_actual': clave,
                                            'password_nueva': 'NuevaClave9', 'password_confirmar': 'NuevaClave9'})
    db.session.refresh(profesional)
    assert profesional.debe_cambiar_password is False
    assert client.get('/dashboard/profesional').status_code == 200


def test_suspender_profesional_cierra_su_acceso(client, app):
    profesional = crear_profesional('dra@test.com')
    crear_cuidador('admin@test.com', rol='admin')
    otro = app.test_client()
    # Cada cliente usa su propio contexto: Flask-Login guarda el usuario en `g`, que es del contexto de aplicación.
    with app.app_context():
        login(otro, 'dra@test.com')
        assert otro.get('/dashboard/profesional').status_code == 200
    with app.app_context():
        login(client, 'admin@test.com')
        client.post(f'/admin/profesionales/{profesional.id}/estado', data={'estado': 'suspendido'})
    with app.app_context():
        assert '/auth/login' in otro.get('/dashboard/profesional').headers['Location']


def test_desbloquear_cuenta(client, app):
    cuidador = crear_cuidador('ana@test.com')
    cuidador.bloqueado_hasta = ahora_utc().replace(year=2099)
    db.session.commit()
    crear_cuidador('admin@test.com', rol='admin')
    login(client, 'admin@test.com')
    client.post(f'/admin/usuarios/cuidador/{cuidador.id}/desbloquear')
    db.session.refresh(cuidador)
    assert not cuidador.esta_bloqueado()


# ---------------------------------------------------------------- Solicitudes de derechos

def test_plazos_en_dias_habiles():
    assert sumar_dias_habiles(date(2026, 10, 2), 1) == date(2026, 10, 5)        # viernes + 1 hábil = lunes
    consulta = SolicitudDerechos(tipo='consulta', fecha_solicitud=ahora_utc().replace(2026, 10, 1, 15))
    reclamo = SolicitudDerechos(tipo='supresion', fecha_solicitud=ahora_utc().replace(2026, 10, 1, 15))
    assert fecha_limite(consulta) == date(2026, 10, 15)                           # 10 hábiles
    assert fecha_limite(reclamo) == date(2026, 10, 22)                            # 15 hábiles


def test_atender_solicitud_notifica_al_titular(client, app):
    cuidador = crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    client.post('/privacidad/solicitudes', data={'tipo': 'consulta', 'nino_id': 0,
                                                 'descripcion': 'Quiero saber qué datos tienen de mí.'})
    client.get('/auth/logout')
    solicitud = SolicitudDerechos.query.one()

    crear_cuidador('admin@test.com', rol='admin')
    login(client, 'admin@test.com')
    listado = client.get('/admin/solicitudes').get_data(as_text=True)
    assert 'Consultar qué datos tiene RespiraKids' in listado and 'días' in listado
    assert client.post(f'/admin/solicitudes/{solicitud.id}', data={'estado': 'resuelta'}).status_code == 400
    client.post(f'/admin/solicitudes/{solicitud.id}',
                data={'estado': 'resuelta', 'respuesta': 'Puedes descargar tus datos desde Mis datos.'})
    db.session.refresh(solicitud)
    assert solicitud.estado == 'resuelta' and solicitud.fecha_respuesta
    assert Notificacion.query.filter_by(usuario_id=cuidador.id, tipo='solicitud_derechos').count() == 1
    client.get('/auth/logout')

    login(client, 'ana@test.com')
    assert 'Puedes descargar tus datos' in client.get('/privacidad/mis-datos').get_data(as_text=True)


# ---------------------------------------------------------------- Auditoría y catálogos

def test_auditoria_filtra_por_evento(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com', 'incorrecta1')
    crear_cuidador('admin@test.com', rol='admin')
    login(client, 'admin@test.com')
    html = client.get('/admin/auditoria?evento=login_fallido').get_data(as_text=True)
    assert '<code>login_fallido</code>' in html and '<code>login_exitoso</code>' not in html


def test_alternar_y_reimportar_conocimiento(client, admin):
    importar_documento()
    entrada = ConocimientoSanitario.query.filter_by(activo=True).first()
    client.post(f'/admin/conocimiento/{entrada.id}/activo')
    db.session.refresh(entrada)
    assert entrada.activo is False
    client.post('/admin/conocimiento/importar')
    db.session.refresh(entrada)
    assert entrada.activo is True


def test_configuracion_no_muestra_secretos(client, admin, app):
    app.config['GEMINI_API_KEY'] = 'clave-super-secreta'
    html = client.get('/admin/configuracion').get_data(as_text=True)
    assert 'clave-super-secreta' not in html and app.config['SECRET_KEY'] not in html


def test_comando_para_crear_administrador(app):
    resultado = app.test_cli_runner().invoke(args=[
        'admin', 'crear', '--correo', 'Jefe@Test.com', '--nombre', 'Ana', '--apellido', 'Ruiz', '--password', PASSWORD])
    assert resultado.exit_code == 0, resultado.output
    assert Cuidador.query.filter_by(correo='jefe@test.com', rol='admin').one().check_password(PASSWORD)
    debil = app.test_cli_runner().invoke(args=[
        'admin', 'crear', '--correo', 'otro@test.com', '--nombre', 'A', '--apellido', 'B', '--password', 'corta'])
    assert debil.exit_code != 0
