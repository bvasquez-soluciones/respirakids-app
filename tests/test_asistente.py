"""Asistente fundamentado en el documento maestro: importación, búsqueda, límites y trazabilidad."""
import json
from datetime import date

import pytest

from app import db
from app.asistente import servicio
from app.asistente.conocimiento import NO_DISPONIBLE, SOLO_PROFESIONAL, buscar, importar_documento, leer_documento
from app.models import ConocimientoSanitario, ConsultaIA, FuenteConocimiento, LogActividad
from tests.conftest import crear_cuidador, crear_nino, crear_profesional, login


@pytest.fixture
def base_conocimiento(app):
    importar_documento()


# ---------------------------------------------------------------- Importación del documento maestro

def test_documento_se_divide_en_fragmentos_trazables():
    fragmentos = leer_documento()
    condiciones = {f.condicion for f in fragmentos}
    assert {'Fiebre', 'Neumonía', 'Bronquiolitis', 'Tos ferina', 'Tuberculosis', 'Asma'} <= condiciones
    assert all(f.url.startswith('https://herramientaclinicaprimerainfancia.minsalud.gov.co/') for f in fragmentos)
    # Las secciones "NO DISPONIBLE EN LA FUENTE CONSULTADA" no se importan.
    assert not any(NO_DISPONIBLE in f.contenido for f in fragmentos)
    assert not any(f.condicion == 'Fiebre' and f.tipo == 'cuidados_casa' for f in fragmentos)


def test_medicamentos_y_dosis_quedan_solo_para_profesionales():
    for f in leer_documento():
        if f.tipo in ('dosis', 'farmacologico', 'manejo'):
            assert f.solo_profesional, f'{f.condicion} · {f.seccion}'
        if 'mg/kg' in f.contenido or 'antibiótico' in f.contenido.lower():
            assert f.solo_profesional, f'{f.condicion} · {f.seccion}'


def test_importar_desactiva_sin_borrar_lo_que_no_es_de_la_fuente(app):
    fuente = FuenteConocimiento(nombre='Fuente no autorizada')
    db.session.add(fuente)
    db.session.flush()
    db.session.add(ConocimientoSanitario(fuente_id=fuente.id, categoria='golpe_leve', nivel='basico',
                                         titulo='Golpes leves', contenido='x', fecha_actualizacion=date(2026, 1, 1),
                                         activo=True))
    db.session.commit()

    resumen = importar_documento()
    antiguo = ConocimientoSanitario.query.filter_by(categoria='golpe_leve').one()
    assert antiguo.activo is False                     # se conserva, pero desactivado
    assert ConocimientoSanitario.query.filter_by(activo=True).count() == resumen['fragmentos']

    importar_documento()                               # idempotente
    assert ConocimientoSanitario.query.filter_by(activo=True).count() == resumen['fragmentos']


# ---------------------------------------------------------------- Búsqueda

def test_busqueda_con_palabras_del_cuidador(base_conocimiento):
    assert buscar('¿Cuáles son los signos de alarma de la neumonía?')[0].titulo == 'Neumonía · Signos de alarma'
    assert buscar('le silba el pecho')[0].categoria == 'bronquiolitis'
    assert buscar('tiene tos perruna y está ronco')[0].categoria == 'laringotraqueitis_crup'
    assert buscar('¿Qué es la varicela?') == []


def test_cuidador_nunca_recibe_contenido_profesional(base_conocimiento):
    for pregunta in ('dosis de salbutamol en bronquiolitis', 'antibióticos para neumonía grave', 'manejo tos ferina'):
        assert all(e.restricciones != SOLO_PROFESIONAL for e in buscar(pregunta))
    assert any(e.restricciones == SOLO_PROFESIONAL
               for e in buscar('dosis de salbutamol en bronquiolitis', incluir_profesional=True))


# ---------------------------------------------------------------- Respuestas

def test_sin_ia_responde_con_los_fragmentos_y_cita_la_fuente(base_conocimiento):
    respuesta = servicio.responder('¿Cuándo debo consultar por fiebre?')
    assert respuesta.tipo == servicio.TIPO_EXTRACTIVA
    assert '[1]' in respuesta.texto and respuesta.fuentes[0]['url'].startswith('https://')


def test_tema_fuera_de_la_fuente_responde_no_disponible(base_conocimiento):
    respuesta = servicio.responder('¿Qué es la varicela?')
    assert respuesta.tipo == servicio.TIPO_NO_DISPONIBLE and NO_DISPONIBLE in respuesta.texto
    assert respuesta.fuentes == []


def test_cuidador_que_pide_dosis_recibe_respuesta_fija(base_conocimiento, monkeypatch):
    llamado = []
    monkeypatch.setattr(servicio, 'generar_respuesta_fundamentada', lambda *a, **k: llamado.append(1))
    respuesta = servicio.responder('¿Cuántos mg de acetaminofén le doy?')
    assert respuesta.tipo == servicio.TIPO_MEDICAMENTOS and 'no recomienda medicamentos' in respuesta.texto
    assert llamado == []                                  # ni siquiera se consulta a la IA


def test_signos_de_alarma_anteponen_aviso_fijo(base_conocimiento):
    respuesta = servicio.responder('se le hunden las costillas y está morado')
    assert respuesta.alarma and respuesta.texto.startswith('⚠️ Atención')


def test_respuesta_generada_que_cita_la_fuente_se_acepta(base_conocimiento, monkeypatch):
    monkeypatch.setattr(servicio, 'generar_respuesta_fundamentada',
                        lambda *a, **k: 'Según Fiebre · Cuándo consultar, consulta si dura más de 7 días [1].')
    respuesta = servicio.responder('¿Cuándo debo consultar por fiebre?')
    assert respuesta.tipo == servicio.TIPO_GENERADA and respuesta.fuentes


@pytest.mark.parametrize('generado', ['Dale mucho líquido y reposo.', 'Consulta al médico [9].', None])
def test_respuesta_generada_sin_cita_valida_se_reemplaza_por_la_fuente(base_conocimiento, monkeypatch, generado):
    monkeypatch.setattr(servicio, 'generar_respuesta_fundamentada', lambda *a, **k: generado)
    respuesta = servicio.responder('¿Cuándo debo consultar por fiebre?')
    assert respuesta.tipo == servicio.TIPO_EXTRACTIVA
    assert 'Dale mucho líquido' not in respuesta.texto


# ---------------------------------------------------------------- Rutas y trazabilidad

def test_consulta_del_cuidador_queda_registrada_y_anonimizada(client, base_conocimiento):
    cuidador = crear_cuidador('ana@test.com')
    crear_nino(cuidador, 'Valentina')
    login(client, 'ana@test.com')
    datos = client.post('/asistente/preguntar', json={'pregunta': 'Valentina tiene calentura hace 9 días'}).get_json()
    assert datos['tipo'] in ('extractiva', 'generada') and datos['fuentes']

    consulta = ConsultaIA.query.one()
    assert 'Valentina' not in consulta.contexto_json
    assert json.loads(consulta.fuentes_citadas)
    assert consulta.resultado == datos['tipo']


def test_contexto_de_evaluacion_solo_para_su_cuidador(client, base_conocimiento):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    crear_cuidador('luis@test.com')
    login(client, 'ana@test.com')
    client.post(f'/sintomas/nino/{nino.id}/nuevo', data={'tiraje_subcostal': 'y'})
    html = client.get('/asistente/?evaluacion=1').get_data(as_text=True)
    assert 'Tiraje subcostal' in html and 'sin cambiar esa clasificación' in html
    client.post('/auth/logout')

    login(client, 'luis@test.com')
    html = client.get('/asistente/?evaluacion=1').get_data(as_text=True)
    assert 'Tiraje subcostal' not in html


def test_consulta_del_profesional_queda_en_auditoria(client, base_conocimiento):
    crear_profesional('dra@test.com')
    login(client, 'dra@test.com')
    datos = client.post('/asistente/preguntar', json={'pregunta': 'dosis de salbutamol en bronquiolitis'}).get_json()
    assert any('Dosis' in f['titulo'] for f in datos['fuentes'])
    assert LogActividad.query.filter_by(accion='consultar_asistente').count() == 1
