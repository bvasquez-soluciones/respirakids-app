"""Consentimiento, política de datos y derechos del titular."""
import json
from datetime import date, timedelta

from app import db
from app.models import Autorizacion, Consentimiento, Nino, SolicitudDerechos
from app.models.privacidad import INVESTIGACION_NINO, POLITICA_DATOS, TERMINOS_USO, TRATAMIENTO_NINO
from app.services.anonimizacion import anonimizar
from tests.conftest import (
    PASSWORD, aceptar_politica, autorizar, crear_cuidador, crear_nino, crear_profesional, login,
)


# ---------------------------------------------------------------- Política de datos

def test_politica_es_publica(client, app):
    respuesta = client.get('/privacidad/')
    assert respuesta.status_code == 200
    assert 'no constituye un diagnóstico médico' in respuesta.get_data(as_text=True)


def test_registro_exige_aceptar_politica(client, app):
    datos = {'nombre': 'Ana', 'apellido': 'Torres', 'correo': 'ana@test.com',
             'password': PASSWORD, 'confirmar_password': PASSWORD}
    assert client.post('/auth/registro', data=datos).status_code == 400

    # Sin aceptar los términos tampoco se crea la cuenta.
    assert client.post('/auth/registro', data={**datos, 'acepta_politica': 'y'}).status_code == 400
    assert client.post('/auth/registro', data={**datos, 'acepta_politica': 'y',
                                               'acepta_terminos': 'y'}).status_code == 302
    politica = Consentimiento.query.filter_by(tipo=POLITICA_DATOS).one()
    terminos = Consentimiento.query.filter_by(tipo=TERMINOS_USO).one()
    assert politica.otorgado and politica.version_politica == app.config['POLITICA_VERSION']
    assert terminos.otorgado and terminos.version_politica == app.config['TERMINOS_VERSION']


def test_usuario_sin_politica_aceptada_es_redirigido(client, app):
    crear_cuidador('ana@test.com', acepta_politica=False)
    login(client, 'ana@test.com')

    respuesta = client.get('/dashboard/cuidador')
    assert respuesta.status_code == 302 and '/privacidad/aceptar' in respuesta.headers['Location']
    assert client.post('/asistente/preguntar', json={'pregunta': 'hola'}).status_code == 403

    assert client.post('/privacidad/aceptar').status_code == 400  # sin marcar la casilla
    respuesta = client.post('/privacidad/aceptar?next=/pacientes/', data={'acepta_politica': 'y', 'acepta_terminos': 'y'})
    assert respuesta.headers['Location'].endswith('/pacientes/')
    assert client.get('/dashboard/cuidador').status_code == 200


def test_nueva_version_de_politica_exige_aceptar_de_nuevo(client, app):
    cuidador = crear_cuidador('ana@test.com', acepta_politica=False)
    aceptar_politica(cuidador, version='0.9')
    login(client, 'ana@test.com')
    assert '/privacidad/aceptar' in client.get('/dashboard/cuidador').headers['Location']


def test_profesional_tambien_debe_aceptar_politica(client, app):
    crear_profesional('dra@test.com', acepta_politica=False)
    login(client, 'dra@test.com')
    assert '/privacidad/aceptar' in client.get('/dashboard/profesional').headers['Location']


# ---------------------------------------------------------------- Consentimiento del niño

def _datos_nino(**cambios):
    datos = {
        'nombre': 'Sofía', 'apellido': 'Torres', 'sexo': 'F',
        'fecha_nacimiento': (date.today() - timedelta(days=400)).isoformat(),
    }
    datos.update(cambios)
    return datos


def test_registrar_nino_exige_autorizacion_de_tratamiento(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    assert client.post('/pacientes/nuevo', data=_datos_nino()).status_code == 400
    assert Nino.query.count() == 0

    assert client.post('/pacientes/nuevo', data=_datos_nino(consentimiento_tratamiento='y')).status_code == 302
    nino = Nino.query.one()
    assert nino.consentimiento_otorgado and not nino.consentimiento_investigacion_otorgado
    tipos = {(c.tipo, c.otorgado) for c in Consentimiento.query.filter_by(nino_id=nino.id)}
    assert tipos == {(TRATAMIENTO_NINO, True), (INVESTIGACION_NINO, False)}


def test_sin_autorizacion_no_se_registran_sintomas(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'), consentimiento=False)
    login(client, 'ana@test.com')
    respuesta = client.post(f'/sintomas/nino/{nino.id}/nuevo', data={'tos': 'on'})
    assert respuesta.status_code == 302
    assert f'/pacientes/{nino.id}/consentimiento' in respuesta.headers['Location']


def test_sin_autorizacion_no_se_comparte_con_profesionales(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'), consentimiento=False)
    crear_profesional('dra@test.com')
    login(client, 'ana@test.com')
    client.post(f'/pacientes/{nino.id}/autorizaciones', data={'correo_profesional': 'dra@test.com', 'confirmar': 'si'})
    assert Autorizacion.query.count() == 0


def test_autorizar_muestra_al_profesional_y_pide_confirmacion(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    dra = crear_profesional('dra@test.com')
    dra.especialidad = 'Pediatría'
    login(client, 'ana@test.com')
    ruta = f'/pacientes/{nino.id}/autorizaciones'
    html = client.post(ruta, data={'correo_profesional': 'dra@test.com'}).get_data(as_text=True)
    # Paso 1: solo muestra quién es; todavía no comparte nada.
    assert '¿Es este el profesional que quieres autorizar?' in html and 'Pediatría' in html
    assert Autorizacion.query.count() == 0
    # Paso 2: al confirmar se otorga el acceso.
    client.post(ruta, data={'correo_profesional': 'dra@test.com', 'confirmar': 'si'})
    assert Autorizacion.query.filter_by(nino_id=nino.id, profesional_id=dra.id, activa=True).count() == 1


def test_profesional_no_ve_nino_sin_autorizacion_de_tratamiento(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'), consentimiento=False)
    autorizar(nino, crear_profesional('dra@test.com'))
    login(client, 'dra@test.com')
    assert client.get(f'/dashboard/profesional?paciente={nino.id}').status_code == 404


def test_otorgar_autorizacion_desde_pagina_de_consentimiento(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'), consentimiento=False)
    login(client, 'ana@test.com')
    assert client.get(f'/pacientes/{nino.id}/consentimiento').status_code == 200
    client.post(f'/pacientes/{nino.id}/consentimiento',
                data={'consentimiento_tratamiento': 'y', 'consentimiento_investigacion': 'y'})
    nino = db.session.get(Nino, nino.id)
    assert nino.consentimiento_otorgado and nino.consentimiento_investigacion_otorgado


def test_revocar_autorizacion_corta_acceso_de_profesionales(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    autorizar(nino, crear_profesional('dra@test.com'))
    login(client, 'ana@test.com')
    client.post(f'/pacientes/{nino.id}/consentimiento', data={})

    assert db.session.get(Nino, nino.id).consentimiento_otorgado is False
    assert Autorizacion.query.filter_by(activa=True).count() == 0
    historial = Consentimiento.query.filter_by(nino_id=nino.id, tipo=TRATAMIENTO_NINO).all()
    assert [c.otorgado for c in historial] == [False]  # el niño de prueba no tenía fila previa


def test_cuidador_no_gestiona_consentimiento_de_nino_ajeno(client, app):
    nino_ana = crear_nino(crear_cuidador('ana@test.com'))
    crear_cuidador('luis@test.com')
    login(client, 'luis@test.com')
    assert client.post(f'/pacientes/{nino_ana.id}/consentimiento', data={}).status_code == 404
    assert db.session.get(Nino, nino_ana.id).consentimiento_otorgado is True


# ---------------------------------------------------------------- Derechos del titular

def test_exportar_mis_datos(client, app):
    cuidador = crear_cuidador('ana@test.com')
    nino = crear_nino(cuidador, 'Sofía')
    login(client, 'ana@test.com')
    client.post(f'/sintomas/nino/{nino.id}/nuevo', data={'tos': 'on'})

    respuesta = client.get('/privacidad/mis-datos/exportar')
    assert respuesta.status_code == 200 and respuesta.mimetype == 'application/json'
    datos = json.loads(respuesta.get_data(as_text=True))
    assert datos['cuenta']['correo'] == 'ana@test.com'
    assert 'password_hash' not in datos['cuenta']
    assert datos['ninos'][0]['datos']['nombre'] == 'Sofía'
    assert datos['ninos'][0]['registros_de_sintomas'][0]['evaluacion']['nivel_riesgo']


def test_profesional_exporta_sus_datos(client, app):
    crear_profesional('dra@test.com')
    login(client, 'dra@test.com')
    datos = json.loads(client.get('/privacidad/mis-datos/exportar').get_data(as_text=True))
    assert datos['cuenta']['correo'] == 'dra@test.com'


def test_radicar_solicitud_de_derechos(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    assert client.get('/privacidad/mis-datos').status_code == 200
    client.post('/privacidad/solicitudes', data={
        'tipo': 'supresion', 'nino_id': nino.id, 'descripcion': 'Quiero eliminar el historial de mi hija.',
    })
    solicitud = SolicitudDerechos.query.one()
    assert solicitud.tipo == 'supresion' and solicitud.nino_id == nino.id and solicitud.estado == 'pendiente'


def test_solicitud_no_puede_referirse_a_nino_ajeno(client, app):
    nino_ana = crear_nino(crear_cuidador('ana@test.com'))
    crear_cuidador('luis@test.com')
    login(client, 'luis@test.com')
    client.post('/privacidad/solicitudes', data={
        'tipo': 'consulta', 'nino_id': nino_ana.id, 'descripcion': 'Información de este niño, por favor.',
    })
    assert SolicitudDerechos.query.count() == 0


def test_editar_perfil_del_cuidador(client, app):
    cuidador = crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    client.post('/dashboard/perfil', data={
        'accion': 'actualizar_perfil', 'nombre': 'Ana  María ', 'apellido': 'Torres', 'telefono': '300 123 4567',
    })
    db.session.refresh(cuidador)
    assert (cuidador.nombre, cuidador.apellido, cuidador.telefono) == ('Ana María', 'Torres', '300 123 4567')


# ---------------------------------------------------------------- Anonimización del asistente

def test_anonimizar_texto():
    texto = 'Mi hija Sofía Pérez (CC 1.023.456.789, sofia@correo.com, tel 300 123 4567) tiene 38.5 de fiebre hace 3 días'
    resultado = anonimizar(texto, ['Sofía', 'Pérez'])
    assert 'Sofía' not in resultado and 'Pérez' not in resultado
    assert '1.023.456.789' not in resultado and '300 123 4567' not in resultado
    assert 'sofia@correo.com' not in resultado
    assert '38.5' in resultado and '3 días' in resultado  # los datos clínicos no se alteran


def test_anonimizar_no_toca_palabras_que_contienen_el_nombre():
    assert anonimizar('Ana tiene tos, la analgesia no ayuda', ['Ana']) == '[nombre] tiene tos, la analgesia no ayuda'


# ---------------------------------------------------------------- Términos y política v2

def test_terminos_publicos_y_exigidos_al_cambiar_de_version(client, app):
    assert 'Términos y condiciones de uso' in client.get('/privacidad/terminos').get_data(as_text=True)
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    assert client.get('/dashboard/cuidador').status_code == 200
    # Una nueva versión de los términos exige aceptarlos de nuevo.
    vigente = app.config['TERMINOS_VERSION']
    app.config['TERMINOS_VERSION'] = '9.9'
    try:
        assert '/privacidad/aceptar' in client.get('/dashboard/cuidador').headers['Location']
        assert client.post('/privacidad/aceptar', data={'acepta_politica': 'y'}).status_code == 400
        client.post('/privacidad/aceptar', data={'acepta_politica': 'y', 'acepta_terminos': 'y'})
        assert client.get('/dashboard/cuidador').status_code == 200
    finally:
        app.config['TERMINOS_VERSION'] = vigente


def test_politica_declara_no_venta_ia_y_sin_garantia_absoluta(client, app):
    politica = client.get('/privacidad/').get_data(as_text=True)
    assert 'no vende, alquila ni comercializa' in politica
    assert 'Decreto 1377 de 2013' in politica and 'artículo 7 de la Ley 1581' in politica
    assert 'Qué se guarda' in politica and 'datos sintéticos' in politica
    assert 'anonimiza' in politica and 'Ningún sistema es completamente infalible' in politica
    assert 'Garantizar la seguridad' not in politica and '[período de conservación por definir]' not in politica
