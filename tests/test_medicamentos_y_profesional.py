"""Medicamentos indicados por profesionales, tomas, notificaciones, panel profesional y zona horaria."""
from datetime import datetime, timedelta

import pytest

from app import db
from app.fechas import a_local, a_utc, fecha_hora
from app.models import (
    MedicamentoRecetado, Notificacion, Receta, TomaMedicamento, VersionRegistro, ahora_utc,
)
from app.services.medicacion import cumplimiento, tomas_pendientes
from tests.conftest import autorizar, crear_cuidador, crear_nino, crear_profesional, login


@pytest.fixture
def escenario(app):
    cuidador = crear_cuidador('ana@test.com')
    nino = crear_nino(cuidador, 'Sofía')
    dra = crear_profesional('dra@test.com')
    otro = crear_profesional('otro@test.com')
    autorizar(nino, dra)
    autorizar(nino, otro)
    crear_profesional('sinacceso@test.com')
    return {'cuidador': cuidador, 'nino': nino, 'dra': dra, 'otro': otro}


def _receta(client, nino_id, **cambios):
    datos = {
        'motivo': 'Control', 'indicaciones_generales': 'Ofrecer líquidos',
        'fecha_inicio': '2026-10-01T08:00',
        'medicamentos-0-nombre': 'Medicamento A', 'medicamentos-0-dosis': '5 ml',
        'medicamentos-0-frecuencia_horas': '8', 'medicamentos-0-duracion_dias': '2',
        'medicamentos-1-nombre': 'Medicamento B', 'medicamentos-1-dosis': '1 gota',
        'medicamentos-1-frecuencia_horas': '12',
    }
    datos.update(cambios)
    return client.post(f'/medicamentos/nino/{nino_id}/nueva', data=datos)


# ---------------------------------------------------------------- Zona horaria

def test_fechas_se_guardan_en_utc_y_se_muestran_en_hora_de_colombia(app):
    utc = datetime(2026, 10, 1, 17, 0)
    assert a_local(utc).hour == 12                 # Colombia: UTC-5
    assert fecha_hora(utc) == '01/10/2026 12:00'
    assert a_utc(datetime(2026, 10, 1, 8, 0)) == datetime(2026, 10, 1, 13, 0)


# ---------------------------------------------------------------- Crear indicaciones

def test_profesional_autorizado_registra_indicacion(client, escenario):
    login(client, 'dra@test.com')
    assert client.get(f'/medicamentos/nino/{escenario["nino"].id}/nueva').status_code == 200
    respuesta = _receta(client, escenario['nino'].id)
    assert respuesta.status_code == 302

    receta = Receta.query.one()
    assert receta.profesional_id == escenario['dra'].id and receta.activa
    a, b = sorted(receta.medicamentos, key=lambda m: m.nombre)
    assert a.fecha_inicio == datetime(2026, 10, 1, 13, 0)              # 08:00 hora local -> 13:00 UTC
    assert len(a.tomas) == 6                                            # 2 días cada 8 horas
    assert [t.hora_programada.hour for t in sorted(a.tomas, key=lambda t: t.hora_programada)][:3] == [13, 21, 5]
    assert b.tomas == []                                                # sin duración: no hay recordatorios

    assert VersionRegistro.query.filter_by(tabla='recetas', registro_id=receta.id, accion='crear').count() == 1
    notificacion = Notificacion.query.filter_by(usuario_tipo='cuidador', tipo='nueva_receta').one()
    assert notificacion.usuario_id == escenario['cuidador'].id


def test_formulario_de_indicacion_valida_cada_medicamento(client, escenario):
    login(client, 'dra@test.com')
    respuesta = _receta(client, escenario['nino'].id, **{'medicamentos-0-dosis': '',
                                                         'medicamentos-1-frecuencia_horas': '0'})
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 400
    assert 'id="medicamentos-0-dosis-error"' in html and 'id="medicamentos-1-frecuencia_horas-error"' in html
    assert Receta.query.count() == 0


@pytest.mark.parametrize('correo,codigo', [('sinacceso@test.com', 404), ('ana@test.com', 403)])
def test_solo_profesionales_autorizados_registran_indicaciones(client, escenario, correo, codigo):
    login(client, correo)
    assert _receta(client, escenario['nino'].id).status_code == codigo
    assert Receta.query.count() == 0


# ---------------------------------------------------------------- Suspender

def test_solo_quien_la_registro_puede_suspenderla(client, escenario):
    login(client, 'dra@test.com')
    _receta(client, escenario['nino'].id)
    receta = Receta.query.one()
    client.get('/auth/logout')

    login(client, 'otro@test.com')
    assert client.post(f'/medicamentos/receta/{receta.id}/suspender').status_code == 403
    client.get('/auth/logout')

    login(client, 'dra@test.com')
    client.post(f'/medicamentos/receta/{receta.id}/suspender')
    db.session.refresh(receta)
    assert receta.activa is False and all(not m.activo for m in receta.medicamentos)
    assert Notificacion.query.filter_by(tipo='receta_suspendida').count() == 1


# ---------------------------------------------------------------- Tomas (cuidador)

def _receta_en_curso(escenario, horas_desde_inicio=10):
    receta = Receta(nino_id=escenario['nino'].id, profesional_id=escenario['dra'].id, activa=True)
    db.session.add(receta)
    db.session.flush()
    medicamento = MedicamentoRecetado(receta_id=receta.id, nombre='Medicamento A', dosis='5 ml',
                                      frecuencia_horas=8, duracion_dias=3, activo=True,
                                      fecha_inicio=ahora_utc() - timedelta(hours=horas_desde_inicio))
    db.session.add(medicamento)
    db.session.flush()
    from app.services.medicacion import programar_tomas
    programar_tomas(medicamento)
    db.session.commit()
    return medicamento


def test_cuidador_marca_y_desmarca_tomas(client, escenario):
    medicamento = _receta_en_curso(escenario)
    toma = sorted(medicamento.tomas, key=lambda t: t.hora_programada)[0]
    login(client, 'ana@test.com')
    assert client.get(f'/medicamentos/nino/{escenario["nino"].id}').status_code == 200

    client.post(f'/medicamentos/toma/{toma.id}/marcar', data={'administrada': '1'})
    db.session.refresh(toma)
    assert toma.administrada and toma.administrado_por_id == escenario['cuidador'].id and toma.hora_administrada

    client.post(f'/medicamentos/toma/{toma.id}/marcar', data={'administrada': '0'})
    db.session.refresh(toma)
    assert not toma.administrada and toma.hora_administrada is None


def test_otro_cuidador_no_marca_tomas(client, escenario):
    medicamento = _receta_en_curso(escenario)
    crear_cuidador('luis@test.com')
    login(client, 'luis@test.com')
    assert client.post(f'/medicamentos/toma/{medicamento.tomas[0].id}/marcar', data={'administrada': '1'}).status_code == 404
    assert client.get(f'/medicamentos/nino/{escenario["nino"].id}').status_code == 404


def test_tomas_pendientes_y_cumplimiento(app, escenario):
    medicamento = _receta_en_curso(escenario, horas_desde_inicio=10)    # tomas cada 8 h desde hace 10 h
    pendientes = tomas_pendientes(escenario['nino'])
    assert len(pendientes) == 5                                          # -10, -2, +6, +14 y +22 h (±24 h)
    primera = sorted(medicamento.tomas, key=lambda t: t.hora_programada)[0]
    primera.administrada = True
    db.session.commit()
    assert cumplimiento(medicamento) == {'administradas': 1, 'vencidas': 2, 'porcentaje': 50}


def test_profesional_ve_el_plan_y_cumplimiento(client, escenario):
    _receta_en_curso(escenario)
    login(client, 'dra@test.com')
    html = client.get(f'/medicamentos/nino/{escenario["nino"].id}').get_data(as_text=True)
    assert 'Medicamento A' in html and 'Cumplimiento' in html and 'Suspender indicación' in html


# ---------------------------------------------------------------- Notificaciones

def test_mensajes_generan_notificaciones_a_la_otra_parte(client, escenario):
    login(client, 'dra@test.com')
    client.post(f'/mensajes/nino/{escenario["nino"].id}', data={'contenido': 'Hola, ¿cómo sigue?'})
    client.get('/auth/logout')

    login(client, 'ana@test.com')
    assert 'rk-bell-badge' in client.get('/dashboard/cuidador').get_data(as_text=True)
    html = client.get('/dashboard/notificaciones').get_data(as_text=True)
    assert 'Nuevo mensaje de un profesional' in html
    assert Notificacion.query.filter_by(usuario_tipo='cuidador', leida=False).count() == 0   # quedaron leídas

    client.post(f'/mensajes/nino/{escenario["nino"].id}', data={'contenido': 'Mejor, gracias'})
    assert Notificacion.query.filter_by(usuario_tipo='profesional', tipo='nuevo_mensaje').count() == 2


# ---------------------------------------------------------------- Panel del profesional

def test_detalle_clinico_de_la_evaluacion(client, escenario):
    login(client, 'ana@test.com')
    client.post(f'/sintomas/nino/{escenario["nino"].id}/nuevo', data={'tiraje_subcostal': 'y', 'tos': 'y'})
    client.get('/auth/logout')

    login(client, 'dra@test.com')
    panel = client.get(f'/dashboard/profesional?paciente={escenario["nino"].id}').get_data(as_text=True)
    assert '<code>R01</code>' in panel and 'Ver detalle clínico' in panel
    html = client.get('/dashboard/profesional/evaluacion/1').get_data(as_text=True)
    assert 'R01' in html and 'se confiere gravedad cuando presenta tiraje subcostal' in html
    assert 'v1-aiepi' in html


def test_detalle_clinico_no_accesible_sin_autorizacion(client, escenario):
    login(client, 'ana@test.com')
    client.post(f'/sintomas/nino/{escenario["nino"].id}/nuevo', data={'tos': 'y'})
    client.get('/auth/logout')
    login(client, 'sinacceso@test.com')
    assert client.get('/dashboard/profesional/evaluacion/1').status_code == 404
