"""Dashboard por niño, ficha, historial, resultado y avatar."""
import json
import re

import pytest

from app import db
from app.models import MedicamentoRecetado, Receta, RegistroSintomas
from app.presentacion import NIVELES, hallazgos_registrados, nivel_info
from app.semaforo import clasificar_riesgo, identificar_senales
from app.services.resumen_nino import resumir_todos
from tests.conftest import crear_cuidador, crear_nino, crear_profesional, login


def _registrar(client, nino, **datos):
    respuesta = client.post(f'/sintomas/nino/{nino.id}/nuevo', data=datos)
    assert respuesta.status_code == 302
    return respuesta.headers['Location']


# ---------------------------------------------------------------- Presentación (fuente única)

def test_todos_los_niveles_tienen_textos_completos():
    for nivel, info in NIVELES.items():
        for clave in ('nombre', 'titulo', 'resumen', 'color', 'icono', 'avatar', 'orden'):
            assert info[clave] not in (None, ''), (nivel, clave)
    assert nivel_info(None) is NIVELES['neutro']
    assert nivel_info('desconocido') is NIVELES['neutro']


def test_textos_no_usan_lenguaje_de_diagnostico():
    for info in NIVELES.values():
        texto = (info['titulo'] + info['resumen']).lower()
        for palabra in ('diagnóstico', 'tiene neumonía', 'enfermedad'):
            assert palabra not in texto


def test_hallazgos_registrados():
    registro = RegistroSintomas(tos=True, cianosis=True, temperatura=38.46)
    assert hallazgos_registrados(registro) == ['Coloración azulada (cianosis)', 'Tos', 'Temperatura 38.5 °C']


def test_senales_coinciden_con_la_clasificacion():
    registro = RegistroSintomas(tos=True, dificultad_respiratoria=True, temperatura=38.2)
    senales = identificar_senales(registro)
    nivel, motivo, _ = clasificar_riesgo(registro)
    assert nivel == 'rojo'
    assert senales['rojo'] == ['dificultad respiratoria reportada']
    assert 'tos presente' in senales['amarillo']
    assert all(s in motivo for s in senales['rojo'])


# ---------------------------------------------------------------- Dashboard

def test_dashboard_muestra_una_tarjeta_por_nino_ordenada_por_riesgo(client, app):
    cuidador = crear_cuidador('ana@test.com')
    sofia = crear_nino(cuidador, 'Sofía')
    mateo = crear_nino(cuidador, 'Mateo')
    crear_nino(cuidador, 'Inactivo', estado='inactivo')
    login(client, 'ana@test.com')
    _registrar(client, sofia, contacto_tuberculosis='on')
    _registrar(client, mateo, tiraje_subcostal='on', tos='on')

    html = client.get('/dashboard/cuidador').get_data(as_text=True)
    assert html.count('class="rk-nino-card ') == 2
    assert 'Inactivo' not in html
    # Mateo (rojo) aparece antes que Sofía (amarillo).
    assert html.index('Mateo') < html.index('Sofía')
    assert NIVELES['rojo']['titulo'] in html and NIVELES['amarillo']['titulo'] in html
    assert 'Posibles señales identificadas' in html
    assert 'Tiraje subcostal' in html


def test_dashboard_sin_ninos_invita_a_registrar(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    assert 'Aún no has registrado ningún niño o niña' in client.get('/dashboard/cuidador').get_data(as_text=True)


def test_resumen_ordena_por_nivel(app):
    cuidador = crear_cuidador('ana@test.com')
    ninos = [crear_nino(cuidador, n) for n in ('Ana', 'Beto')]
    resumenes = resumir_todos(ninos)
    assert [r.nivel for r in resumenes] == ['neutro', 'neutro']
    assert [r.nino.nombre for r in resumenes] == ['Ana', 'Beto']


def test_dashboard_muestra_medicamentos_indicados_por_profesional(client, app):
    cuidador = crear_cuidador('ana@test.com')
    nino = crear_nino(cuidador)
    dra = crear_profesional('dra@test.com')
    receta = Receta(nino_id=nino.id, profesional_id=dra.id, activa=True)
    db.session.add(receta)
    db.session.flush()
    db.session.add(MedicamentoRecetado(receta_id=receta.id, nombre='Medicamento X', dosis='5 ml',
                                       frecuencia_horas=8, activo=True))
    db.session.commit()

    login(client, 'ana@test.com')
    html = client.get('/dashboard/cuidador').get_data(as_text=True)
    assert 'Medicamento X' in html and 'cada 8 h' in html
    assert 'no por RespiraKids' in html


# ---------------------------------------------------------------- Avatar

@pytest.mark.parametrize('sexo', ['F', 'M'])
@pytest.mark.parametrize('nivel,texto', [('verde', 'sin señales'), ('amarillo', 'requiere vigilancia'),
                                         ('rojo', 'se identificaron posibles señales de alarma'), (None, 'aún no hay evaluaciones')])
def test_avatar_por_sexo_y_estado(app, sexo, nivel, texto):
    from app.models import Nino
    plantilla = app.jinja_env.from_string('{% from "macros/avatar.html" import avatar %}{{ avatar(n, nivel) }}')
    svg = plantilla.render(n=Nino(nombre='Sofía', sexo=sexo), nivel=nivel)
    assert svg.startswith('<svg') and 'role="img"' in svg
    assert re.search(rf'aria-label="Avatar de Sofía: {texto}', svg)
    # Las coletas solo se dibujan en la versión de niña.
    assert ('cx="24" cy="54"' in svg) == (sexo == 'F')


# ---------------------------------------------------------------- Resultado, ficha e historial

def test_resultado_muestra_senales_orientacion_y_lo_registrado(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    destino = _registrar(client, nino, cianosis='on', tos='on', dias_tos='16', temperatura='38.3',
                         observaciones='Le cuesta dormir')
    html = client.get(destino).get_data(as_text=True)

    assert NIVELES['rojo']['titulo'] in html
    assert 'Posibles señales de alarma' in html and 'Señales que requieren valoración' in html
    assert 'Orientación' in html and 'Busca atención en un servicio de salud de inmediato' in html
    assert 'Temperatura 38.3 °C' in html and 'Le cuesta dormir' in html
    assert 'no constituye un diagnóstico médico' in html


def test_ficha_del_nino(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'), 'Sofía')
    login(client, 'ana@test.com')
    _registrar(client, nino, perdida_peso='on')
    html = client.get(f'/pacientes/{nino.id}').get_data(as_text=True)
    assert 'Identificación' in html and 'Antecedentes y condiciones de base' in html
    assert 'Medicamentos indicados' in html and 'Últimas evaluaciones' in html
    assert NIVELES['amarillo']['titulo'] in html


def test_ficha_de_nino_ajeno_no_accesible(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    crear_cuidador('luis@test.com')
    login(client, 'luis@test.com')
    assert client.get(f'/pacientes/{nino.id}').status_code == 404


def test_historial_incluye_linea_de_tiempo_y_datos_de_evolucion(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    _registrar(client, nino, tos='on', dias_tos='20', temperatura='38.1')
    _registrar(client, nino)
    html = client.get(f'/sintomas/nino/{nino.id}').get_data(as_text=True)

    assert html.count('rk-linea-tiempo__item ') == 2
    assert 'Ver detalle de la evaluación' in html
    datos = json.loads(re.search(r'<script id="datos-evolucion" type="application/json">(.*?)</script>', html).group(1))
    assert datos['niveles'] == [2, 1]  # amarillo y luego verde, en orden cronológico
    assert datos['temperaturas'] == [38.1, None]
