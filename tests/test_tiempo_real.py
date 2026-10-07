"""Actualización sin recargar: contadores de la barra y mensajes nuevos de una conversación."""
from app.models import Notificacion
from tests.conftest import autorizar, crear_cuidador, crear_nino, crear_profesional, login


def _escenario():
    ana = crear_cuidador('ana@test.com')
    sofia = crear_nino(ana, 'Sofía')
    dra = crear_profesional('dra@test.com')
    autorizar(sofia, dra)
    return ana, sofia, dra


def test_contadores_de_la_barra(client, app):
    _, sofia, dra = _escenario()
    login(client, 'ana@test.com')
    assert client.get('/dashboard/estado').get_json() == {'notificaciones': 0, 'alertas': 0, 'solicitudes': 0}
    client.post(f'/mensajes/nino/{sofia.id}/solicitar', data={'motivo': 'Tiene tos y fiebre desde ayer.'})
    client.post('/auth/logout')
    login(client, 'dra@test.com')
    datos = client.get('/dashboard/estado').get_json()
    assert datos['solicitudes'] == 1 and datos['notificaciones'] == 1


def test_mensajes_nuevos_sin_recargar(client, app):
    _, sofia, dra = _escenario()
    login(client, 'ana@test.com')
    ruta = f'/mensajes/nino/{sofia.id}/profesional/{dra.id}'
    client.post(ruta, data={'contenido': 'Hola doctora'})
    primero = client.get(f'{ruta}/nuevos?desde=0').get_json()['mensajes']
    assert [m['contenido'] for m in primero] == ['Hola doctora'] and primero[0]['propio']
    client.post('/auth/logout')

    login(client, 'dra@test.com')
    client.post(f'/mensajes/nino/{sofia.id}', data={'contenido': 'Hola, ¿cómo sigue?'})
    client.post('/auth/logout')

    login(client, 'ana@test.com')
    nuevos = client.get(f'{ruta}/nuevos?desde={primero[0]["id"]}').get_json()['mensajes']
    assert [m['contenido'] for m in nuevos] == ['Hola, ¿cómo sigue?'] and not nuevos[0]['propio']
    # Al recibir el mensaje en pantalla, su aviso queda leído.
    assert Notificacion.query.filter_by(usuario_tipo='cuidador', leida=False).count() == 0


def test_nadie_lee_conversaciones_ajenas_por_esta_via(client, app):
    _, sofia, dra = _escenario()
    crear_cuidador('otra@test.com')
    crear_profesional('otro@test.com')
    login(client, 'otra@test.com')
    assert client.get(f'/mensajes/nino/{sofia.id}/profesional/{dra.id}/nuevos?desde=0').status_code == 404
    client.post('/auth/logout')
    login(client, 'otro@test.com')
    assert client.get(f'/mensajes/nino/{sofia.id}/nuevos?desde=0').status_code == 404
