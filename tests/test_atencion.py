"""Atención por mensajes: solicitud, primer profesional que acepta, cupo, autorización y cierre del caso."""
import pytest

from app import db
from app.models import Autorizacion, Mensaje, Notificacion, SolicitudAtencion
from tests.conftest import crear_cuidador, crear_nino, crear_profesional, login

MOTIVO = 'Tiene tos desde hace tres días y hoy amaneció con fiebre.'


@pytest.fixture
def clinica(app):
    ana = crear_cuidador('ana@test.com')
    sofia = crear_nino(ana, 'Sofía')
    dra = crear_profesional('dra@test.com')
    otro = crear_profesional('otro@test.com')
    pausado = crear_profesional('pausado@test.com')
    pausado.disponible = False
    db.session.commit()
    return {'ana': ana, 'sofia': sofia, 'dra': dra, 'otro': otro, 'pausado': pausado}


def _solicitar(client, nino, motivo=MOTIVO):
    login(client, 'ana@test.com')
    respuesta = client.post(f'/mensajes/nino/{nino.id}/solicitar', data={'motivo': motivo})
    client.post('/auth/logout')
    return respuesta


def _atender(client, correo, solicitud):
    login(client, correo)
    respuesta = client.post(f'/mensajes/solicitud/{solicitud.id}/atender')
    client.post('/auth/logout')
    return respuesta


def test_solicitud_llega_solo_a_profesionales_disponibles(client, clinica):
    respuesta = _solicitar(client, clinica['sofia'])
    solicitud = SolicitudAtencion.query.one()
    assert respuesta.headers['Location'].endswith(f'/mensajes/solicitud/{solicitud.id}')
    assert solicitud.estado == 'pendiente' and solicitud.motivo == MOTIVO
    avisados = {n.usuario_id for n in Notificacion.query.filter_by(tipo='nueva_solicitud')}
    assert avisados == {clinica['dra'].id, clinica['otro'].id}  # el profesional en pausa no recibe aviso
    # Una segunda solicitud mientras hay una abierta no duplica.
    _solicitar(client, clinica['sofia'], 'Otra vez la misma consulta, por favor.')
    assert SolicitudAtencion.query.count() == 1

    login(client, 'ana@test.com')
    html = client.get(f'/mensajes/solicitud/{solicitud.id}').get_data(as_text=True)
    assert 'Conectando con un profesional de salud' in html
    assert client.get(f'/mensajes/solicitud/{solicitud.id}/estado').get_json() == {'estado': 'pendiente'}


def test_el_primero_que_acepta_atiende_el_caso(client, clinica):
    _solicitar(client, clinica['sofia'])
    solicitud = SolicitudAtencion.query.one()
    _atender(client, 'dra@test.com', solicitud)
    # El segundo profesional llega tarde: no se le asigna.
    tarde = _atender(client, 'otro@test.com', solicitud)
    assert tarde.headers['Location'].endswith('/mensajes/solicitudes')
    db.session.refresh(solicitud)
    assert solicitud.estado == 'asignada' and solicitud.profesional_id == clinica['dra'].id
    # El motivo abre la conversación privada con la Dra.; el cuidador recibe el aviso.
    primero = Mensaje.query.filter_by(profesional_conversacion_id=clinica['dra'].id).one()
    assert primero.contenido == MOTIVO and primero.autor_tipo == 'cuidador'
    assert Notificacion.query.filter_by(usuario_tipo='cuidador', tipo='solicitud_asignada').count() == 1


def test_cuidador_autoriza_el_expediente(client, clinica):
    _solicitar(client, clinica['sofia'])
    solicitud = SolicitudAtencion.query.one()
    _atender(client, 'dra@test.com', solicitud)
    login(client, 'ana@test.com')
    html = client.get(f'/mensajes/solicitud/{solicitud.id}').get_data(as_text=True)
    assert '¿Autorizas que' in html and 'acceda a toda la información de Sofía' in html
    client.post(f'/mensajes/solicitud/{solicitud.id}/acceso', data={'respuesta': 'si'})
    client.post('/auth/logout')
    assert Autorizacion.query.filter_by(nino_id=clinica['sofia'].id, profesional_id=clinica['dra'].id,
                                        activa=True).count() == 1
    login(client, 'dra@test.com')
    assert client.get(f'/dashboard/profesional?paciente={clinica["sofia"].id}').status_code == 200


def test_sin_autorizacion_conversa_pero_no_ve_el_expediente(client, clinica):
    _solicitar(client, clinica['sofia'])
    solicitud = SolicitudAtencion.query.one()
    _atender(client, 'dra@test.com', solicitud)
    login(client, 'ana@test.com')
    client.post(f'/mensajes/solicitud/{solicitud.id}/acceso', data={'respuesta': 'no'})
    client.post('/auth/logout')
    assert Autorizacion.query.count() == 0

    login(client, 'dra@test.com')
    html = client.get(f'/mensajes/nino/{clinica["sofia"].id}').get_data(as_text=True)
    assert MOTIVO in html and 'Sin acceso al expediente' in html
    client.post(f'/mensajes/nino/{clinica["sofia"].id}', data={'contenido': '¿Cuánta fiebre tiene ahora?'})
    detalle = client.get(f'/dashboard/profesional?paciente={clinica["sofia"].id}').get_data(as_text=True)
    assert 'Ves el resumen del semáforo' in detalle and 'Antecedentes y medicamentos' not in detalle
    client.post('/auth/logout')
    # Un profesional sin relación con el caso no puede abrir la conversación.
    login(client, 'otro@test.com')
    assert client.get(f'/mensajes/nino/{clinica["sofia"].id}').status_code == 404


def test_cupo_de_casos(client, app, clinica):
    app.config['CUPO_CASOS_POR_PROFESIONAL'] = 1
    try:
        lucas = crear_nino(clinica['ana'], 'Lucas')
        _solicitar(client, clinica['sofia'])
        _atender(client, 'dra@test.com', SolicitudAtencion.query.one())
        _solicitar(client, lucas)
        segunda = SolicitudAtencion.query.filter_by(nino_id=lucas.id).one()
        _atender(client, 'dra@test.com', segunda)  # cupo lleno: no se asigna
        db.session.refresh(segunda)
        assert segunda.estado == 'pendiente'
        login(client, 'dra@test.com')
        assert 'Alcanzaste tu cupo' in client.get('/mensajes/solicitudes').get_data(as_text=True)
        # Al cerrar un caso se libera el cupo y la conversación sigue disponible.
        primera = SolicitudAtencion.query.filter_by(nino_id=clinica['sofia'].id).one()
        client.post(f'/mensajes/solicitud/{primera.id}/cerrar')
        db.session.refresh(primera)
        assert primera.estado == 'cerrada'
        assert client.get(f'/mensajes/nino/{clinica["sofia"].id}').status_code == 200
        client.post(f'/mensajes/solicitud/{segunda.id}/atender')
        db.session.refresh(segunda)
        assert segunda.estado == 'asignada'
    finally:
        app.config['CUPO_CASOS_POR_PROFESIONAL'] = 15


def test_otro_cuidador_no_ve_la_solicitud(client, clinica):
    _solicitar(client, clinica['sofia'])
    solicitud = SolicitudAtencion.query.one()
    crear_cuidador('otra@test.com')
    login(client, 'otra@test.com')
    assert client.get(f'/mensajes/solicitud/{solicitud.id}').status_code == 404
    assert client.post(f'/mensajes/solicitud/{solicitud.id}/acceso', data={'respuesta': 'si'}).status_code == 404


def test_semaforo_de_la_clinica(client, clinica):
    sin_consentimiento = crear_nino(clinica['ana'], 'Lucas', consentimiento=False)
    login(client, 'otro@test.com')  # no tiene ninguna autorización
    html = client.get('/dashboard/semaforo').get_data(as_text=True)
    assert 'Sofía' in html and sin_consentimiento.nombre not in html
    assert 'Ver expediente' not in html
    client.post('/auth/logout')
    login(client, 'ana@test.com')
    assert client.get('/dashboard/semaforo').status_code in (302, 403)


def test_disponibilidad(client, clinica):
    login(client, 'dra@test.com')
    client.post('/mensajes/disponibilidad', data={'disponible': 'no'})
    db.session.refresh(clinica['dra'])
    assert clinica['dra'].disponible is False
    assert 'Pausaste las nuevas solicitudes' in client.get('/mensajes/solicitudes').get_data(as_text=True)


def test_panel_muestra_todos_los_pacientes_y_protege_el_expediente(client, clinica):
    sin_consentimiento = crear_nino(clinica['ana'], 'Lucas', consentimiento=False)
    login(client, 'otro@test.com')  # no tiene ninguna autorización
    panel = client.get('/dashboard/profesional').get_data(as_text=True)
    assert 'Sofía' in panel and sin_consentimiento.nombre not in panel
    # Sin autorización: resumen del semáforo, no el expediente.
    detalle = client.get(f'/dashboard/profesional?paciente={clinica["sofia"].id}').get_data(as_text=True)
    assert 'Ves el resumen del semáforo' in detalle and 'Antecedentes y medicamentos' not in detalle
    assert client.get(f'/dashboard/profesional?paciente={sin_consentimiento.id}').status_code == 404


# ---------------------------------------------------------------- Autorización previa y solicitud desde el resultado

def _autorizacion_previa(client, nino, atencion):
    login(client, 'ana@test.com')
    datos = {'consentimiento_tratamiento': 'y'}
    if atencion:
        datos['consentimiento_atencion'] = 'y'
    client.post(f'/pacientes/{nino.id}/consentimiento', data=datos)
    client.post('/auth/logout')


def test_autorizacion_previa_da_acceso_al_profesional_que_atiende(client, clinica):
    from app.models import Consentimiento
    _autorizacion_previa(client, clinica['sofia'], atencion=True)
    assert Consentimiento.query.filter_by(nino_id=clinica['sofia'].id, tipo='acceso_profesional_atencion',
                                          otorgado=True).count() == 1
    _solicitar(client, clinica['sofia'])
    solicitud = SolicitudAtencion.query.one()
    _atender(client, 'dra@test.com', solicitud)
    db.session.refresh(solicitud)
    # Sin preguntar: acceso inmediato solo para quien atiende.
    assert solicitud.acceso == 'otorgado'
    assert Autorizacion.query.filter_by(nino_id=clinica['sofia'].id, activa=True).count() == 1
    login(client, 'ana@test.com')
    destino = client.get(f'/mensajes/solicitud/{solicitud.id}').headers['Location']
    assert destino.endswith(f'/mensajes/nino/{clinica["sofia"].id}/profesional/{clinica["dra"].id}')
    client.post('/auth/logout')
    login(client, 'otro@test.com')
    assert client.get(f'/mensajes/nino/{clinica["sofia"].id}').status_code == 404


def test_autorizacion_previa_desmarcada_por_defecto_y_revocable(client, clinica):
    login(client, 'ana@test.com')
    html = client.get('/pacientes/nuevo').get_data(as_text=True)
    assert 'id="consentimiento_atencion"' in html and 'consentimiento_atencion" type="checkbox" value="y" checked' not in html
    client.post('/auth/logout')
    _autorizacion_previa(client, clinica['sofia'], atencion=True)
    _autorizacion_previa(client, clinica['sofia'], atencion=False)  # la retira
    _solicitar(client, clinica['sofia'])
    solicitud = SolicitudAtencion.query.one()
    _atender(client, 'dra@test.com', solicitud)
    db.session.refresh(solicitud)
    assert solicitud.acceso is None and Autorizacion.query.count() == 0  # vuelve a preguntarse


def test_hablar_con_un_profesional_desde_el_resultado(client, clinica):
    login(client, 'ana@test.com')
    client.post(f'/sintomas/nino/{clinica["sofia"].id}/nuevo', data={'tos': 'on'})
    from app.models import Evaluacion
    html = client.get(f'/sintomas/resultado/{Evaluacion.query.one().id}').get_data(as_text=True)
    assert '¿Quieres que un profesional revise este resultado?' in html and 'Registré los síntomas de Sofía' in html
    client.post(f'/mensajes/nino/{clinica["sofia"].id}/solicitar',
                data={'motivo': 'Registré los síntomas de Sofía: tos. ¿Qué debo vigilar?'})
    assert SolicitudAtencion.query.one().estado == 'pendiente'
    assert 'Conectando con un profesional' in client.get(
        f'/sintomas/resultado/{Evaluacion.query.one().id}').get_data(as_text=True)
