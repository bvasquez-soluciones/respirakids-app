"""Centro de ayuda: manual para cuidadores (público, accesible y coherente con la aplicación)."""
import re

from tests.conftest import crear_cuidador, login


def test_manual_publico_sin_sesion(client):
    for ruta in ('/ayuda/', '/ayuda/cuidadores'):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 200, ruta


def test_manual_disponible_sin_aceptar_politica(client, app):
    crear_cuidador('ana@test.com', acepta_politica=False)
    login(client, 'ana@test.com')
    assert client.get('/ayuda/cuidadores', follow_redirects=False).status_code == 200


def test_manual_cubre_los_modulos_del_cuidador(client):
    html = client.get('/ayuda/cuidadores').get_data(as_text=True)
    for texto in ('Primeros pasos', 'Entiende el semáforo', 'Registrar síntomas', 'Hablar con un profesional',
                  'Medicamentos', 'Asistente virtual', 'Tus datos y privacidad', 'Olvidé mi contraseña',
                  'nota de voz', 'Mejoró'):
        assert texto in html, texto
    # Aviso de urgencias y de que no es un diagnóstico
    texto = ' '.join(html.split())
    assert '123' in texto and 'no es un servicio de urgencias' in texto
    assert 'es una orientación, no un diagnóstico' in texto


def test_semaforo_explorador_accesible(client):
    html = client.get('/ayuda/cuidadores').get_data(as_text=True)
    for nivel in ('rojo', 'amarillo', 'verde', 'neutro'):
        assert f'aria-controls="panel-{nivel}"' in html
        assert f'id="panel-{nivel}"' in html
    # Solo el primer panel visible de entrada; el resto se muestra con las pestañas
    assert len(re.findall(r'role="tabpanel"[^>]*\bhidden\b', html)) == 3


def test_preguntas_con_ancla_unica(client):
    html = client.get('/ayuda/cuidadores').get_data(as_text=True)
    ids = re.findall(r'<details class="rk-pregunta" id="([^"]+)"', html)
    assert len(ids) >= 20 and len(ids) == len(set(ids))


def test_enlace_de_ayuda_en_menu_y_pie(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    html = client.get('/dashboard/cuidador').get_data(as_text=True)
    assert 'href="/ayuda/cuidadores"' in html and 'href="/ayuda/"' in html
