"""Supresión por anonimización (solicitudes de derechos) y período de conservación."""
from datetime import timedelta

from app import db, mail
from app.models import (
    Autorizacion, ConsultaIA, Consentimiento, Cuidador, Evaluacion, Mensaje, Nino, Notificacion, Profesional,
    SolicitudDerechos, ahora_utc,
)
from tests.conftest import PASSWORD, autorizar, crear_cuidador, crear_nino, crear_profesional, login


def _registrar_sintomas(client, nino, **datos):
    assert client.post(f'/sintomas/nino/{nino.id}/nuevo', data=datos).status_code == 302


def _preparar_familia(client):
    """Cuidadora con dos niños, uno con síntomas, mensaje, consulta al asistente y notificación."""
    ana = crear_cuidador('ana@test.com')
    ana.telefono = '3001234567'
    sofia = crear_nino(ana, 'Sofía')
    sofia.apellido, sofia.numero_documento = 'Torres', '1012345678'
    lucas = crear_nino(ana, 'Lucas')
    dra = crear_profesional('dra@test.com')
    autorizar(sofia, dra)
    db.session.add_all([
        Mensaje(nino_id=sofia.id, autor_tipo='cuidador', autor_cuidador_id=ana.id, contenido='Sofía tosió toda la noche'),
        ConsultaIA(nino_id=sofia.id, cuidador_id=ana.id, resultado='ok'),
        Notificacion(usuario_id=ana.id, usuario_tipo='cuidador', tipo='nuevo_mensaje', titulo='Mensaje',
                     contenido='La Dra. escribió sobre Sofía.', recurso='mensajes', recurso_id=sofia.id),
        Consentimiento(usuario_id=ana.id, usuario_tipo='cuidador', nino_id=sofia.id, tipo='tratamiento_datos_nino',
                       version_politica='2.0', otorgado=True),
    ])
    db.session.commit()
    login(client, 'ana@test.com')
    _registrar_sintomas(client, sofia, tos='on', observaciones='Vive con la abuela Rosa en Chía')
    client.post('/auth/logout')
    return ana, sofia, lucas, dra


def _solicitar(usuario, nino=None):
    solicitud = SolicitudDerechos(usuario_id=usuario.id, usuario_tipo=usuario.tipo_usuario, tipo='supresion',
                                  nino_id=nino.id if nino else None, descripcion='Quiero que borren mis datos.')
    db.session.add(solicitud)
    db.session.commit()
    return solicitud


def _ejecutar(client, solicitud, confirmacion='ANONIMIZAR'):
    crear_cuidador('admin@test.com', rol='admin')
    login(client, 'admin@test.com')
    with mail.record_messages() as buzon:
        respuesta = client.post(f'/admin/solicitudes/{solicitud.id}/suprimir', data={'confirmacion': confirmacion})
    return respuesta, buzon


def test_supresion_de_un_nino_lo_anonimiza_y_desvincula(client, app):
    ana, sofia, lucas, dra = _preparar_familia(client)
    evaluaciones = Evaluacion.query.filter_by(nino_id=sofia.id).count()
    solicitud = _solicitar(ana, sofia)

    respuesta, buzon = _ejecutar(client, solicitud)
    assert respuesta.status_code == 302
    db.session.expire_all()
    sofia = db.session.get(Nino, sofia.id)
    # Sin datos identificables y sin vínculo con la cuidadora.
    assert (sofia.nombre, sofia.apellido, sofia.numero_documento) == ('Anonimizado', None, None)
    assert sofia.cuidador_id is None and sofia.estado == 'anonimizado' and sofia.fecha_nacimiento.day == 1
    assert all(r.observaciones is None for r in sofia.registros_sintomas)
    assert Mensaje.query.filter_by(nino_id=sofia.id).count() == 0
    assert ConsultaIA.query.filter_by(nino_id=sofia.id).count() == 0
    assert Notificacion.query.filter_by(recurso_id=sofia.id).count() == 0
    assert not Autorizacion.query.filter_by(nino_id=sofia.id).one().activa
    # Se conservan sin identificar los datos clínicos y la prueba legal.
    assert Evaluacion.query.filter_by(nino_id=sofia.id).count() == evaluaciones
    assert Consentimiento.query.filter_by(nino_id=sofia.id).count() >= 1
    # El otro niño y la cuenta de la cuidadora no cambian.
    assert db.session.get(Nino, lucas.id).nombre == 'Lucas' and db.session.get(Cuidador, ana.id).nombre != 'Anonimizado'
    # Solicitud resuelta y constancia enviada al titular.
    assert db.session.get(SolicitudDerechos, solicitud.id).estado == 'resuelta'
    assert len(buzon) == 1 and buzon[0].recipients == ['ana@test.com'] and 'Sofía' in buzon[0].body


def test_supresion_de_la_cuenta_cierra_el_acceso(client, app):
    ana, sofia, lucas, dra = _preparar_familia(client)
    solicitud = _solicitar(ana)
    _, buzon = _ejecutar(client, solicitud)
    db.session.expire_all()
    ana = db.session.get(Cuidador, ana.id)
    assert ana.nombre == 'Anonimizado' and ana.telefono is None and ana.correo.endswith('@anonimizado.invalid')
    assert all(n.estado == 'anonimizado' and n.cuidador_id is None for n in Nino.query.all())
    assert ConsultaIA.query.count() == 0
    assert len(buzon) == 1 and buzon[0].recipients == ['ana@test.com']
    # Nadie puede volver a entrar: ni con el correo original ni con la contraseña anterior.
    client.post('/auth/logout')
    assert login(client, 'ana@test.com', PASSWORD).status_code == 401
    assert not ana.check_password(PASSWORD)


def test_confirmacion_incorrecta_no_modifica_nada(client, app):
    ana, sofia, _, _ = _preparar_familia(client)
    solicitud = _solicitar(ana, sofia)
    respuesta, buzon = _ejecutar(client, solicitud, confirmacion='si')
    assert respuesta.headers['Location'].endswith(f'/admin/solicitudes/{solicitud.id}')
    db.session.expire_all()
    assert db.session.get(Nino, sofia.id).nombre == 'Sofía' and len(buzon) == 0
    assert db.session.get(SolicitudDerechos, solicitud.id).estado == 'pendiente'


def test_no_se_puede_anonimizar_un_nino_de_otra_persona(client, app):
    ana, sofia, _, _ = _preparar_familia(client)
    otra = crear_cuidador('otra@test.com')
    solicitud = _solicitar(otra, sofia)  # pide suprimir un niño que no es suyo
    respuesta, _ = _ejecutar(client, solicitud)
    assert respuesta.status_code == 400
    db.session.expire_all()
    assert db.session.get(Nino, sofia.id).nombre == 'Sofía'


def test_supresion_de_profesional(client, app):
    _, sofia, _, dra = _preparar_familia(client)
    solicitud = _solicitar(dra)
    _ejecutar(client, solicitud)
    db.session.expire_all()
    dra = db.session.get(Profesional, dra.id)
    assert dra.nombre == 'Anonimizado' and dra.estado_aprobacion == 'suspendido' and dra.numero_licencia is None
    assert not Autorizacion.query.filter_by(profesional_id=dra.id, activa=True).count()


def test_conservacion_lista_y_solo_anonimiza_con_ejecutar(app):
    antigua = crear_cuidador('antigua@test.com')
    antigua.fecha_registro = ahora_utc() - timedelta(days=365 * 3)
    crear_nino(antigua, 'Ana')
    reciente = crear_cuidador('reciente@test.com')
    db.session.commit()
    runner = app.test_cli_runner()

    resultado = runner.invoke(args=['privacidad', 'conservacion'])
    assert 'cuidador #%d' % antigua.id in resultado.output and 'cuidador #%d' % reciente.id not in resultado.output
    assert db.session.get(Cuidador, antigua.id).nombre != 'Anonimizado'  # sin --ejecutar no cambia nada

    runner.invoke(args=['privacidad', 'conservacion', '--ejecutar'])
    db.session.expire_all()
    assert db.session.get(Cuidador, antigua.id).nombre == 'Anonimizado'
    assert db.session.get(Cuidador, reciente.id).nombre != 'Anonimizado'
