"""Seguimiento de evolución reportado por el cuidador (mejoró / sigue igual / empeoró)."""
from datetime import timedelta

from app import db
from app.models import Evaluacion, SeguimientoEvolucion
from app.presentacion import nivel_info
from tests.conftest import autorizar, crear_cuidador, crear_nino, crear_profesional, login


def _registrar_sintomas(client, nino, **datos):
    assert client.post(f'/sintomas/nino/{nino.id}/nuevo', data=datos).status_code == 302


def _seguimiento(client, nino, estado):
    return client.post(f'/sintomas/nino/{nino.id}/seguimiento', data={'estado': estado})


def test_seguimiento_se_guarda_y_no_cambia_la_clasificacion(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    _registrar_sintomas(client, nino, tos='on')
    evaluacion = Evaluacion.query.one()
    nivel_antes = evaluacion.nivel_riesgo

    respuesta = _seguimiento(client, nino, 'empeoro')
    # Empeoró (o mejoró) abre una reevaluación rápida: el semáforo solo lo cambia el motor clínico.
    assert respuesta.headers['Location'].endswith(f'/sintomas/nino/{nino.id}/nuevo?reevaluacion=empeoro')
    seguimiento = SeguimientoEvolucion.query.one()
    assert (seguimiento.estado, seguimiento.evaluacion_id) == ('empeoro', evaluacion.id)
    # Solo se guarda la percepción del cuidador: no hay evaluación nueva ni cambia el nivel.
    assert Evaluacion.query.count() == 1 and db.session.get(Evaluacion, evaluacion.id).nivel_riesgo == nivel_antes

    html = client.get('/dashboard/cuidador').get_data(as_text=True)
    assert 'Indicaste «Empeoró»' in html and 'Registrar síntomas ahora' in html


def test_otro_cuidador_no_puede_registrar_seguimiento(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    crear_cuidador('otro@test.com')
    login(client, 'ana@test.com')
    _registrar_sintomas(client, nino, tos='on')
    client.post('/auth/logout')
    login(client, 'otro@test.com')
    assert _seguimiento(client, nino, 'mejoro').status_code == 404
    assert SeguimientoEvolucion.query.count() == 0


def test_estado_invalido_o_sin_evaluacion(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    # Sin evaluación previa no hay con qué comparar: se pide registrar síntomas.
    assert _seguimiento(client, nino, 'mejoro').headers['Location'].endswith(f'/sintomas/nino/{nino.id}/nuevo')
    _registrar_sintomas(client, nino, tos='on')
    assert _seguimiento(client, nino, 'curado').status_code == 400
    assert SeguimientoEvolucion.query.count() == 0


def test_seguimiento_exige_consentimiento(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'), consentimiento=False)
    login(client, 'ana@test.com')
    assert '/consentimiento' in _seguimiento(client, nino, 'mejoro').headers['Location']


def test_una_evaluacion_nueva_reinicia_el_seguimiento(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    _registrar_sintomas(client, nino, tos='on')
    _seguimiento(client, nino, 'igual')
    assert 'Indicaste «Sigue igual»' in client.get('/dashboard/cuidador').get_data(as_text=True)
    # Un registro posterior genera otra evaluación: se vuelve a preguntar desde cero.
    primera = Evaluacion.query.one()
    primera.fecha = primera.fecha - timedelta(hours=2)
    SeguimientoEvolucion.query.one().fecha = primera.fecha + timedelta(minutes=5)
    db.session.commit()
    _registrar_sintomas(client, nino, tos='on')
    assert 'Indicaste «' not in client.get('/dashboard/cuidador').get_data(as_text=True)


def test_profesional_autorizado_ve_la_evolucion_y_se_exporta(client, app):
    cuidadora = crear_cuidador('ana@test.com')
    nino = crear_nino(cuidadora)
    dra = crear_profesional('dra@test.com')
    autorizar(nino, dra)
    login(client, 'ana@test.com')
    _registrar_sintomas(client, nino, tos='on')
    _seguimiento(client, nino, 'mejoro')
    exportado = client.get('/privacidad/mis-datos/exportar').get_data(as_text=True)
    assert 'seguimientos_de_evolucion' in exportado and 'mejoro' in exportado
    client.post('/auth/logout')
    login(client, 'dra@test.com')
    html = client.get(f'/dashboard/profesional?paciente={nino.id}').get_data(as_text=True)
    assert 'Evolución reportada por el cuidador' in html and 'Mejoró' in html


# ---------------------------------------------------------------- Avatar e historial

def test_expresion_del_avatar_refleja_la_evolucion_sin_cambiar_el_nivel():
    from app.presentacion import expresion_avatar
    assert expresion_avatar('rojo') == 'enfermo'
    assert expresion_avatar('rojo', 'mejoro') == 'normal'      # tranquila, no celebración, mientras siga en rojo
    assert expresion_avatar('amarillo', 'mejoro') == 'normal'
    assert expresion_avatar('verde', 'mejoro') == 'feliz'
    assert expresion_avatar('verde', 'empeoro') == 'enfermo'
    assert expresion_avatar('amarillo', 'igual') == 'preocupado'


def test_mejoro_cambia_el_avatar_y_queda_en_el_historial(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    _registrar_sintomas(client, nino, cianosis='on')
    nivel = Evaluacion.query.one().nivel_riesgo
    assert nivel in ('amarillo', 'rojo')
    _seguimiento(client, nino, 'mejoro')

    html = client.get('/dashboard/cuidador').get_data(as_text=True)
    assert 'nina-normal-figura.webp' in html and 'evolución reportada: mejoró' in html
    # El nivel clínico no cambia: sigue el mismo texto de estado y se invita a actualizarlo.
    assert nivel_info(nivel)['titulo'] in html and 'Actualizar el estado' in html

    historial = client.get(f'/sintomas/nino/{nino.id}').get_data(as_text=True)
    assert 'rk-linea-tiempo__item--seguimiento' in historial and 'Mejoró' in historial


def test_historial_del_profesional_incluye_el_seguimiento(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    dra = crear_profesional('dra@test.com')
    autorizar(nino, dra)
    login(client, 'ana@test.com')
    _registrar_sintomas(client, nino, tos='on')
    _seguimiento(client, nino, 'empeoro')
    client.post('/auth/logout')
    login(client, 'dra@test.com')
    html = client.get(f'/dashboard/profesional?paciente={nino.id}').get_data(as_text=True)
    assert 'Evolución reportada: Empeoró' in html and 'nina-enfermo.webp' in html


def test_sigue_igual_vuelve_al_inicio(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    _registrar_sintomas(client, nino, tos='on')
    assert _seguimiento(client, nino, 'igual').headers['Location'].endswith(f'#nino-{nino.id}')


def test_mejoro_lleva_a_reevaluar_y_el_motor_actualiza_el_semaforo(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    _registrar_sintomas(client, nino, cianosis='on')
    assert Evaluacion.query.one().nivel_riesgo == 'rojo'

    destino = _seguimiento(client, nino, 'mejoro').headers['Location']
    assert destino.endswith('?reevaluacion=mejoro')
    assert 'marca solo lo que observas' in client.get(destino).get_data(as_text=True)

    # El cuidador guarda lo que observa hoy (nada): el motor AIEPI recalcula y el semáforo pasa a verde.
    assert client.post(destino, data={}).status_code == 302
    ultima = Evaluacion.query.order_by(Evaluacion.id.desc()).first()
    assert Evaluacion.query.count() == 2 and ultima.nivel_riesgo == 'verde'
    html = client.get('/dashboard/cuidador').get_data(as_text=True)
    assert nivel_info('verde')['titulo'] in html and 'rk-nino-card--verde' in html
    # El seguimiento queda en el historial, antes de la nueva evaluación.
    historial = client.get(f'/sintomas/nino/{nino.id}').get_data(as_text=True)
    assert historial.index('Mejoró') > historial.index(nivel_info('verde')['titulo'])
