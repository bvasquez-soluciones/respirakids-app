"""Guía interactiva para cuidadores nuevos: la etapa sale de lo que el cuidador ya hizo y cada paso apunta
a un elemento real de la página."""
import json
import re

from app import db
from app.models import Evaluacion, RegistroSintomas
from tests.conftest import crear_cuidador, crear_nino, crear_profesional, login


def _guia(client, ruta):
    html = client.get(ruta).get_data(as_text=True)
    encontrado = re.search(r'<script type="application/json" id="rk-guia-datos">(.*?)</script>', html, re.S)
    return (json.loads(encontrado.group(1)) if encontrado else None), html


def _objetivos_presentes(datos, html):
    """Todos los pasos apuntan a un [data-guia] que existe (y al niño/a correcto, si aplica)."""
    for paso in datos['pasos']:
        assert f'data-guia="{paso["objetivo"]}"' in html, paso['objetivo']
        if 'nino' in paso:
            patron = rf'data-guia="{paso["objetivo"]}"\s+data-guia-nino="{paso["nino"]}"'
            assert re.search(patron, html), paso


def _evaluar(nino, nivel='verde'):
    registro = RegistroSintomas(nino_id=nino.id, tos=True)
    db.session.add(registro)
    db.session.flush()
    evaluacion = Evaluacion(nino_id=nino.id, registro_sintomas_id=registro.id, nivel_riesgo=nivel)
    db.session.add(evaluacion)
    db.session.commit()
    return evaluacion


def test_cuidador_nuevo_recibe_bienvenida_y_paso_registrar_nino(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    datos, html = _guia(client, '/dashboard/cuidador')
    assert datos['etapa'] == 'registrar_nino'
    assert datos['bienvenida']['titulo'] == '¡Bienvenido a RespiraKids! 👋'
    assert 'realizar su seguimiento' in datos['bienvenida']['texto']
    assert datos['pasos'][0]['accion'] is True
    _objetivos_presentes(datos, html)
    assert 'js/guia.js' in html


def test_formulario_de_registro_guia_datos_autorizacion_y_guardar(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    datos, html = _guia(client, '/pacientes/nuevo')
    assert [p['objetivo'] for p in datos['pasos']] == ['datos-nino', 'autorizacion', 'guardar-nino']
    assert datos['bienvenida'] is None
    _objetivos_presentes(datos, html)


def test_sin_autorizacion_la_guia_pide_autorizar(client, app):
    ana = crear_cuidador('ana@test.com')
    sofia = crear_nino(ana, 'Sofía', consentimiento=False)
    login(client, 'ana@test.com')
    for ruta in ('/dashboard/cuidador', '/pacientes/'):
        datos, html = _guia(client, ruta)
        assert datos['etapa'] == 'autorizar' and datos['pasos'][0]['nino'] == sofia.id
        _objetivos_presentes(datos, html)
    datos, html = _guia(client, f'/pacientes/{sofia.id}/consentimiento')
    _objetivos_presentes(datos, html)


def test_con_nino_autorizado_la_guia_lleva_a_registrar_sintomas(client, app):
    ana = crear_cuidador('ana@test.com')
    sofia = crear_nino(ana, 'Sofía')
    login(client, 'ana@test.com')
    for ruta in ('/dashboard/cuidador', '/pacientes/'):
        datos, html = _guia(client, ruta)
        assert datos['etapa'] == 'registrar_sintomas'
        assert 'Sofía' in datos['pasos'][0]['titulo'] and 'tu niña' in datos['pasos'][0]['texto']
        _objetivos_presentes(datos, html)
    datos, html = _guia(client, f'/sintomas/nino/{sofia.id}/nuevo')
    assert [p['objetivo'] for p in datos['pasos']] == ['secciones', 'grupo-alarma', 'grupo-respiracion',
                                                     'guardar-sintomas']
    _objetivos_presentes(datos, html)


def test_primer_resultado_cierra_la_guia_y_luego_desaparece(client, app):
    ana = crear_cuidador('ana@test.com')
    sofia = crear_nino(ana, 'Sofía')
    primera = _evaluar(sofia)
    login(client, 'ana@test.com')
    datos, html = _guia(client, f'/sintomas/resultado/{primera.id}')
    assert datos['etapa'] == 'primer_resultado'
    _objetivos_presentes(datos, html)
    assert _guia(client, '/dashboard/cuidador')[0] is None
    segunda = _evaluar(sofia)
    assert _guia(client, f'/sintomas/resultado/{segunda.id}')[0] is None


def test_la_guia_se_puede_volver_a_ver_desde_ayuda(client, app):
    ana = crear_cuidador('ana@test.com')
    _evaluar(crear_nino(ana, 'Sofía'))
    login(client, 'ana@test.com')
    assert 'guia=1' in client.get('/ayuda/cuidadores').get_data(as_text=True)
    datos, html = _guia(client, '/dashboard/cuidador?guia=1')
    assert datos['etapa'] == 'recorrido' and datos['forzada'] is True
    _objetivos_presentes(datos, html)


def test_profesionales_y_administradores_no_ven_la_guia(client, app):
    crear_profesional('dra@test.com')
    login(client, 'dra@test.com')
    assert _guia(client, '/dashboard/profesional')[0] is None
    client.post('/auth/logout')
    crear_cuidador('admin@test.com', rol='admin')
    login(client, 'admin@test.com')
    assert _guia(client, '/dashboard/cuidador')[0] is None


def test_la_guia_no_expone_datos_de_otros_ni_codigo_ejecutable(client, app):
    ana = crear_cuidador('ana@test.com')
    crear_nino(ana, '</script><script>alert(1)</script>')
    login(client, 'ana@test.com')
    html = client.get('/dashboard/cuidador').get_data(as_text=True)
    bloque = re.search(r'<script type="application/json" id="rk-guia-datos">(.*?)</script>', html, re.S).group(1)
    assert '<script>' not in bloque and '\\u003c' in bloque
