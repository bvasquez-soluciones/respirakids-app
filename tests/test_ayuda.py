"""Centro de ayuda: manual para cuidadores (público, accesible y coherente con la aplicación)."""
import re

from tests.conftest import crear_cuidador, crear_profesional, login


def test_manual_publico_sin_sesion(client):
    assert client.get('/ayuda/', follow_redirects=True).status_code == 200
    assert client.get('/ayuda/cuidadores').status_code == 200


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


def test_cuidador_va_directo_a_su_manual(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    respuesta = client.get('/ayuda/')
    assert respuesta.status_code == 302 and respuesta.headers['Location'].endswith('/ayuda/cuidadores')


def test_cada_usuario_ve_solo_sus_manuales(app):
    from app.ayuda.routes import MANUALES, manuales_para

    class Usuario:
        def __init__(self, rol):
            self.rol, self.is_authenticated = rol, rol is not None

    claves = {rol: {m['clave'] for m in manuales_para(Usuario(rol))} for rol in (None, 'cuidador', 'admin', 'profesional')}
    assert claves['cuidador'] == {'cuidadores'}
    assert claves['profesional'] == {'profesionales'}
    # Ningún manual de otro rol se cuela: el profesional no ve el de cuidadores
    assert 'cuidadores' not in claves['profesional']
    for m in MANUALES:
        if 'profesional' not in m['roles']:
            assert m['clave'] not in claves['profesional']


def test_profesional_va_directo_a_su_manual(client, app):
    crear_profesional('dra@test.com')
    login(client, 'dra@test.com')
    html = client.get('/dashboard/profesional').get_data(as_text=True)
    assert 'href="/ayuda/profesionales"' in html and 'href="/ayuda/cuidadores"' not in html
    respuesta = client.get('/ayuda/')
    assert respuesta.status_code == 302 and respuesta.headers['Location'].endswith('/ayuda/profesionales')


def test_cuidador_no_ve_el_manual_del_profesional(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    html = client.get('/dashboard/cuidador').get_data(as_text=True)
    assert 'href="/ayuda/profesionales"' not in html


def test_visitante_elige_entre_cuidador_y_profesional(client):
    html = client.get('/ayuda/').get_data(as_text=True)
    assert 'href="/ayuda/cuidadores"' in html and 'href="/ayuda/profesionales"' in html


def test_manual_profesional_cubre_sus_modulos(client, app):
    html = ' '.join(client.get('/ayuda/profesionales').get_data(as_text=True).split())
    for texto in ('Primeros pasos', 'El semáforo para priorizar', 'contraseña temporal', 'Mis pacientes',
                  'expediente completo', 'Atender', 'Pausar nuevas solicitudes', 'Cerrar caso', '+ Indicación',
                  'Suspender indicación', 'Exportar PDF', 'auditoría', 'no es un diagnóstico'):
        assert texto in html, texto
    assert f"{app.config['CUPO_CASOS_POR_PROFESIONAL']} casos abiertos" in html
    ids = re.findall(r'<details class="rk-pregunta" id="([^"]+)"', html)
    assert len(ids) >= 20 and len(ids) == len(set(ids))


def test_profesional_con_clave_temporal_puede_leer_su_manual(client, app):
    from app import db
    dra = crear_profesional('dra@test.com')
    dra.debe_cambiar_password = True
    db.session.commit()
    login(client, 'dra@test.com')
    assert client.get('/ayuda/profesionales').status_code == 200
