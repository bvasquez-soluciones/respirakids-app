"""Videollamadas de telemedicina: solo el profesional del caso llama, solo sus dos participantes entran, el
cuidador acepta con consentimiento, nada se graba y las señales técnicas se borran al terminar."""
from datetime import timedelta

from app import db
from app.models import Mensaje, SenalVideollamada, Videollamada, ahora_utc
from app.services import atencion
from tests.conftest import crear_cuidador, crear_nino, crear_profesional, login


def _caso():
    """Ana pidió atención para Sofía y la Dra. la atiende."""
    ana = crear_cuidador('ana@test.com')
    sofia = crear_nino(ana, 'Sofía')
    dra = crear_profesional('dra@test.com')
    solicitud, _ = atencion.crear_solicitud(sofia, ana, 'Tiene tos desde ayer.')
    atencion.aceptar(solicitud.id, dra)
    return ana, sofia, dra, solicitud


def _iniciar(client, solicitud):
    login(client, 'dra@test.com')
    respuesta = client.post(f'/videollamada/nino/{solicitud.nino_id}/iniciar')
    assert respuesta.status_code == 302
    return Videollamada.query.one()


def _cambiar_a(client, correo):
    client.post('/auth/logout')
    login(client, correo)


def test_el_profesional_del_caso_inicia_y_el_cuidador_recibe_el_aviso(client, app):
    _, sofia, _, solicitud = _caso()
    llamada = _iniciar(client, solicitud)
    assert llamada.estado == 'llamando' and llamada.nino_id == sofia.id
    assert client.get(f'/videollamada/{llamada.id}').status_code == 200
    _cambiar_a(client, 'ana@test.com')
    datos = client.get('/dashboard/estado').get_json()
    assert datos['llamada']['url'] == f'/videollamada/{llamada.id}'
    assert 'te está llamando por video' in datos['llamada']['texto']
    html = client.get(f'/videollamada/{llamada.id}').get_data(as_text=True)
    assert 'name="consentimiento"' in html and 'No se graba' in html


def test_solo_el_profesional_que_atiende_al_paciente_puede_llamar(client, app):
    _, sofia, _, _ = _caso()
    crear_profesional('otro@test.com')
    login(client, 'otro@test.com')
    assert client.post(f'/videollamada/nino/{sofia.id}/iniciar').status_code == 404
    _cambiar_a(client, 'ana@test.com')
    assert client.post(f'/videollamada/nino/{sofia.id}/iniciar').status_code == 404
    assert Videollamada.query.count() == 0


def test_caso_cerrado_sin_autorizacion_no_permite_llamar(client, app):
    _, sofia, _, solicitud = _caso()
    atencion.cerrar(solicitud)
    login(client, 'dra@test.com')
    assert client.post(f'/videollamada/nino/{sofia.id}/iniciar').status_code == 404
    assert Videollamada.query.count() == 0


def test_paciente_autorizado_sin_caso_abierto_si_se_puede_llamar(client, app):
    from tests.conftest import autorizar
    ana = crear_cuidador('ana@test.com')
    sofia = crear_nino(ana, 'Sofía')
    dra = crear_profesional('dra@test.com')
    autorizar(sofia, dra)
    login(client, 'dra@test.com')
    html = client.get(f'/dashboard/profesional?paciente={sofia.id}').get_data(as_text=True)
    assert f'/videollamada/nino/{sofia.id}/iniciar' in html  # botón en el expediente
    assert f'/videollamada/nino/{sofia.id}/iniciar' in client.get(f'/mensajes/nino/{sofia.id}').get_data(as_text=True)
    client.post(f'/videollamada/nino/{sofia.id}/iniciar')
    llamada = Videollamada.query.one()
    assert llamada.solicitud_id is None and llamada.cuidador_id == ana.id and llamada.estado == 'llamando'


def test_revocar_la_autorizacion_corta_la_llamada(client, app):
    from app.models import Autorizacion
    from tests.conftest import autorizar
    ana = crear_cuidador('ana@test.com')
    sofia = crear_nino(ana, 'Sofía')
    dra = crear_profesional('dra@test.com')
    autorizacion = autorizar(sofia, dra)
    login(client, 'dra@test.com')
    client.post(f'/videollamada/nino/{sofia.id}/iniciar')
    llamada = Videollamada.query.one()
    _cambiar_a(client, 'ana@test.com')
    client.post(f'/videollamada/{llamada.id}/responder', data={'respuesta': 'aceptar', 'consentimiento': 'si'})
    client.post(f'/pacientes/{sofia.id}/autorizaciones/{autorizacion.id}/revocar')
    assert db.session.get(Autorizacion, autorizacion.id).activa is False
    assert db.session.get(Videollamada, llamada.id).estado == 'finalizada'


def test_nadie_ajeno_entra_a_la_llamada(client, app):
    _, _, _, solicitud = _caso()
    llamada = _iniciar(client, solicitud)
    crear_cuidador('otra@test.com')
    crear_profesional('otro@test.com')
    for correo in ('otra@test.com', 'otro@test.com'):
        _cambiar_a(client, correo)
        for ruta in (f'/videollamada/{llamada.id}', f'/videollamada/{llamada.id}/estado'):
            assert client.get(ruta).status_code == 404, (correo, ruta)
        assert client.post(f'/videollamada/{llamada.id}/senal', json={'tipo': 'oferta', 'datos': {}}).status_code == 404
        assert client.post(f'/videollamada/{llamada.id}/colgar').status_code == 404
    assert db.session.get(Videollamada, llamada.id).estado == 'llamando'


def test_contestar_exige_consentimiento(client, app):
    _, _, _, solicitud = _caso()
    llamada = _iniciar(client, solicitud)
    _cambiar_a(client, 'ana@test.com')
    client.post(f'/videollamada/{llamada.id}/responder', data={'respuesta': 'aceptar'})
    assert db.session.get(Videollamada, llamada.id).estado == 'llamando'
    client.post(f'/videollamada/{llamada.id}/responder', data={'respuesta': 'aceptar', 'consentimiento': 'si'})
    llamada = db.session.get(Videollamada, llamada.id)
    assert llamada.estado == 'en_curso' and llamada.consentimiento_fecha is not None


def test_el_cuidador_puede_rechazar(client, app):
    _, _, _, solicitud = _caso()
    llamada = _iniciar(client, solicitud)
    _cambiar_a(client, 'ana@test.com')
    client.post(f'/videollamada/{llamada.id}/responder', data={'respuesta': 'rechazar'})
    assert db.session.get(Videollamada, llamada.id).estado == 'rechazada'
    assert 'llamada' not in client.get('/dashboard/estado').get_json()


def test_las_senales_llegan_solo_a_la_otra_parte(client, app):
    _, _, _, solicitud = _caso()
    llamada = _iniciar(client, solicitud)
    _cambiar_a(client, 'ana@test.com')
    client.post(f'/videollamada/{llamada.id}/responder', data={'respuesta': 'aceptar', 'consentimiento': 'si'})
    _cambiar_a(client, 'dra@test.com')
    oferta = {'type': 'offer', 'sdp': 'v=0 prueba'}
    assert client.post(f'/videollamada/{llamada.id}/senal', json={'tipo': 'oferta', 'datos': oferta}).status_code == 201
    assert client.get(f'/videollamada/{llamada.id}/estado').get_json()['senales'] == []  # no recibe las propias
    _cambiar_a(client, 'ana@test.com')
    datos = client.get(f'/videollamada/{llamada.id}/estado?desde=0').get_json()
    assert datos['estado'] == 'en_curso' and datos['senales'][0]['datos'] == oferta
    ultimo = datos['senales'][0]['id']
    assert client.get(f'/videollamada/{llamada.id}/estado?desde={ultimo}').get_json()['senales'] == []


def test_senales_no_validas_se_rechazan(client, app):
    _, _, _, solicitud = _caso()
    llamada = _iniciar(client, solicitud)
    url = f'/videollamada/{llamada.id}/senal'
    assert client.post(url, json={'tipo': 'script', 'datos': {}}).status_code == 400
    assert client.post(url, json={'tipo': 'oferta', 'datos': 'x' * 30000}).status_code == 400


def test_colgar_registra_la_duracion_y_borra_las_senales(client, app):
    _, sofia, dra, solicitud = _caso()
    llamada = _iniciar(client, solicitud)
    _cambiar_a(client, 'ana@test.com')
    client.post(f'/videollamada/{llamada.id}/responder', data={'respuesta': 'aceptar', 'consentimiento': 'si'})
    client.post(f'/videollamada/{llamada.id}/senal', json={'tipo': 'candidato', 'datos': {'candidate': 'x'}})
    llamada = db.session.get(Videollamada, llamada.id)
    llamada.fecha_respuesta = ahora_utc() - timedelta(minutes=7, seconds=5)
    db.session.commit()
    respuesta = client.post(f'/videollamada/{llamada.id}/colgar', headers={'Accept': 'application/json'})
    assert respuesta.get_json()['estado'] == 'finalizada'
    assert SenalVideollamada.query.count() == 0
    constancia = Mensaje.query.filter(Mensaje.contenido.like('%Videollamada finalizada%')).one()
    assert constancia.profesional_conversacion_id == dra.id and '7 min 05 s' in constancia.contenido
    # La sala muestra el resultado y no carga el video.
    html = client.get(f'/videollamada/{llamada.id}').get_data(as_text=True)
    assert 'La videollamada terminó' in html and 'videollamada.js' not in html


def test_sin_respuesta_queda_perdida(client, app):
    _, _, _, solicitud = _caso()
    llamada = _iniciar(client, solicitud)
    llamada.fecha_creacion = ahora_utc() - timedelta(seconds=app.config['VIDEOLLAMADA_TIMBRE_SEGUNDOS'] + 5)
    db.session.commit()
    assert client.get(f'/videollamada/{llamada.id}/estado').get_json()['estado'] == 'perdida'
    assert Mensaje.query.filter(Mensaje.contenido.like('%Videollamada perdida%')).count() == 1


def test_si_un_lado_se_desconecta_la_llamada_termina(client, app):
    _, _, _, solicitud = _caso()
    llamada = _iniciar(client, solicitud)
    _cambiar_a(client, 'ana@test.com')
    client.post(f'/videollamada/{llamada.id}/responder', data={'respuesta': 'aceptar', 'consentimiento': 'si'})
    llamada = db.session.get(Videollamada, llamada.id)
    llamada.pulso_profesional = ahora_utc() - timedelta(seconds=app.config['VIDEOLLAMADA_SIN_PULSO_SEGUNDOS'] + 5)
    db.session.commit()
    assert client.get(f'/videollamada/{llamada.id}/estado').get_json()['estado'] == 'finalizada'


def test_cerrar_el_caso_sin_autorizacion_cuelga_la_llamada(client, app):
    _, _, _, solicitud = _caso()
    llamada = _iniciar(client, solicitud)
    client.post(f'/mensajes/solicitud/{solicitud.id}/cerrar')
    assert db.session.get(Videollamada, llamada.id).estado == 'cancelada'


def test_boton_de_videollamada_en_la_conversacion(client, app):
    _, sofia, _, solicitud = _caso()
    login(client, 'dra@test.com')
    html = client.get(f'/mensajes/nino/{sofia.id}').get_data(as_text=True)
    assert f'/videollamada/nino/{sofia.id}/iniciar' in html


def test_servidores_turn_con_credenciales_temporales(app):
    from app.services.videollamadas import servidores_ice
    app.config.update(TURN_URLS=['turn:turn.clinica.test:3478'], TURN_SECRETO='secreto-de-prueba',
                      WEBRTC_STUN_URLS=['stun:turn.clinica.test:3478'])
    with app.test_request_context():
        servidores = servidores_ice('cuidador-1')
    turn = servidores[1]
    vence, identidad = turn['username'].split(':')
    assert identidad == 'cuidador-1' and int(vence) > 0 and turn['credential']
    assert 'secreto-de-prueba' not in str(servidores)


def test_la_supresion_desvincula_las_llamadas(client, app):
    from app.services.supresion import anonimizar_nino
    _, sofia, _, solicitud = _caso()
    llamada = _iniciar(client, solicitud)
    anonimizar_nino(sofia)
    db.session.commit()
    llamada = db.session.get(Videollamada, llamada.id)
    assert llamada.cuidador_id is None and llamada.estado == 'cancelada'


def test_la_camara_solo_se_permite_a_la_propia_aplicacion():
    from app import create_app
    from config import TestingConfig
    TestingConfig.TALISMAN_ENABLED = True
    try:
        app = create_app('testing')
        cabecera = app.test_client().get('/').headers.get('Permissions-Policy', '')
    finally:
        TestingConfig.TALISMAN_ENABLED = False
    assert 'camera=(self)' in cabecera and 'microphone=(self)' in cabecera and 'geolocation=()' in cabecera


def test_politica_y_terminos_informan_la_videollamada(client, app):
    politica = ' '.join(client.get('/privacidad/').get_data(as_text=True).split())
    assert 'no se graban la imagen ni el sonido' in politica and 'Videollamadas:' in politica
    terminos = ' '.join(client.get('/privacidad/terminos').get_data(as_text=True).split())
    assert 'Resolución 2654 de 2019' in terminos and 'No se graban' in terminos
