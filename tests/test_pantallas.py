"""Cada pantalla de cada rol debe renderizar sin errores con datos reales."""
from tests.conftest import autorizar, crear_cuidador, crear_nino, crear_patologia, crear_profesional, login


def _preparar(client):
    ana = crear_cuidador('ana@test.com')
    nino = crear_nino(ana, 'Sofía')
    crear_patologia(nino)
    dra = crear_profesional('dra@test.com')
    autorizar(nino, dra)
    login(client, 'ana@test.com')
    client.post(f'/sintomas/nino/{nino.id}/nuevo', data={'quejido': 'on', 'temperatura': '39.2'})
    client.post(f'/mensajes/nino/{nino.id}/profesional/{dra.id}', data={'contenido': 'Hola doctora'})
    return nino


def test_pantallas_del_cuidador(client, app):
    nino = _preparar(client)
    for ruta in (
        '/dashboard/cuidador', '/dashboard/perfil', '/pacientes/', '/pacientes/nuevo',
        f'/pacientes/{nino.id}/editar', f'/pacientes/{nino.id}/autorizaciones', f'/pacientes/{nino.id}/patologias',
        f'/sintomas/nino/{nino.id}', f'/sintomas/nino/{nino.id}/nuevo', '/sintomas/resultado/1',
        f'/mensajes/nino/{nino.id}', '/asistente/', f'/pacientes/{nino.id}/consentimiento',
        '/privacidad/', '/privacidad/mis-datos', '/privacidad/aceptar', f'/pacientes/{nino.id}',
    ):
        assert client.get(ruta).status_code == 200, ruta


def test_pantallas_del_profesional(client, app):
    nino = _preparar(client)
    client.post('/auth/logout')
    login(client, 'dra@test.com')
    for ruta in (
        '/dashboard/profesional', f'/dashboard/profesional?paciente={nino.id}',
        f'/dashboard/profesional?paciente={nino.id}&rango=todo', '/dashboard/reportes',
        '/dashboard/alertas', '/dashboard/ajustes', f'/mensajes/nino/{nino.id}', '/privacidad/mis-datos',
    ):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 200, ruta
    assert 'Sofía' in client.get('/dashboard/alertas').get_data(as_text=True)

    pdf = client.get('/dashboard/reportes/exportar-pdf')
    assert pdf.status_code == 200 and pdf.mimetype == 'application/pdf'


def test_pantalla_del_admin(client, app):
    crear_cuidador('admin@test.com', rol='admin')
    login(client, 'admin@test.com')
    assert client.get('/dashboard/admin').status_code == 302
    assert client.get('/admin/').status_code == 200
