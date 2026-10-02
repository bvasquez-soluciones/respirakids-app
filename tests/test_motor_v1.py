"""Motor clínico v1 (AIEPI): cada regla, sus umbrales literales, los huecos de la fuente y la trazabilidad."""
import json
import os

import pytest

from app.clinica import reglas_v1
from app.clinica.documentacion import RUTA_DOCUMENTO, generar_markdown
from app.clinica.motor import DatosEvaluacion, evaluar_v1
from app.models import Evaluacion
from config import ProductionConfig
from tests.conftest import crear_cuidador, crear_nino, login


def evaluar(edad_meses=24, **datos):
    return evaluar_v1(DatosEvaluacion(edad_meses=edad_meses, **datos))


def ids(resultado):
    return {s['regla_id'] for s in resultado.senales}


# ---------------------------------------------------------------- Integridad del conjunto de reglas

def test_todas_las_reglas_son_trazables_y_estan_pendientes_de_validacion():
    vistos = set()
    for regla in reglas_v1.REGLAS:
        assert regla.id not in vistos
        vistos.add(regla.id)
        assert regla.nivel in ('rojo', 'amarillo')
        assert regla.criterio and regla.fuente and regla.orientacion and regla.senal
        assert regla.validacion, f'{regla.id} debe listar qué debe validar un profesional'
        if regla.origen == 'fuente':
            assert reglas_v1.MAPEO_COLOR in regla.validacion
        else:
            assert regla.origen == 'salvaguarda' and 'NO PROVIENE DE LA FUENTE' in regla.criterio


ENFERMEDADES = ('neumonía', 'bronquiolitis', 'tuberculosis', 'tos ferina', 'crup', 'mastoiditis', 'asma')


def test_textos_para_el_cuidador_no_diagnostican():
    for regla in reglas_v1.REGLAS:
        orientacion, senal = regla.orientacion.lower(), regla.senal.lower()
        for palabra in ('diagnóstico de', 'padece', 'tiene ') :
            assert palabra not in orientacion + senal, regla.id
        # La orientación nunca nombra enfermedades.
        assert not any(e in orientacion for e in ENFERMEDADES), regla.id
        # La señal solo puede nombrarlas como "compatibles con" una definición, o al describir un contacto.
        if any(e in senal for e in ENFERMEDADES):
            assert 'compatibles con' in senal or 'contacto' in senal, regla.id


def test_documento_de_validacion_esta_sincronizado_con_el_codigo():
    with open(RUTA_DOCUMENTO, encoding='utf-8') as archivo:
        assert archivo.read() == generar_markdown(), 'Ejecuta: flask reglas documentar'


# ---------------------------------------------------------------- Resultado general

def test_sin_hallazgos_es_verde_con_orientacion_de_la_fuente():
    resultado = evaluar()
    assert resultado.nivel == 'verde' and resultado.senales == []
    assert 'no significa que no haya enfermedad' in resultado.recomendaciones
    assert 'lavado frecuente de manos' in resultado.recomendaciones


def test_sintomas_leves_sin_criterios_de_la_fuente_son_verde():
    # Tos, congestión y fiebre de 38.5 °C no son, por sí solos, criterios de alarma ni de consulta en la fuente.
    resultado = evaluar(tos=True, congestion_nasal=True, secrecion_nasal=True, temperatura=38.5)
    assert resultado.nivel == 'verde'
    assert any('superior a 38 °C' in aviso for aviso in resultado.avisos)


def test_el_nivel_final_es_el_mayor():
    resultado = evaluar(contacto_tuberculosis=True, cianosis=True)
    assert resultado.nivel == 'rojo'
    assert [s['nivel'] for s in resultado.senales] == ['rojo', 'amarillo']


# ---------------------------------------------------------------- Reglas rojas de signo directo

@pytest.mark.parametrize('campo,regla', [
    ('tiraje_subcostal', 'R01'), ('cianosis', 'R02'), ('incapacidad_beber_liquidos', 'R03'),
    ('quejido', 'R04'), ('aleteo_nasal', 'R05'), ('apnea', 'R06'), ('estridor', 'R08'),
    ('alteracion_conciencia', 'R09'), ('convulsion', 'R10'), ('rigidez_cuello', 'R12'),
    ('abombamiento_fontanela', 'R13'), ('petequias', 'R14'), ('edema_retroauricular', 'R15'),
])
def test_signos_de_alarma_son_rojo(campo, regla):
    resultado = evaluar(**{campo: True})
    assert resultado.nivel == 'rojo' and regla in ids(resultado)


def test_temperatura_mayor_de_40_es_rojo():
    assert evaluar(temperatura=40.0).nivel == 'verde'      # la fuente dice ">40"
    assert evaluar(temperatura=40.1).nivel == 'rojo'


# ---------------------------------------------------------------- Taquipnea (A01): umbrales literales

@pytest.mark.parametrize('edad,limite', [(0, 60), (1, 60), (3, 50), (11, 50), (12, 40), (59, 40)])
def test_taquipnea_por_edad(edad, limite):
    assert evaluar(edad, frecuencia_respiratoria=limite).nivel == 'verde'          # igual al umbral: no es ">"
    resultado = evaluar(edad, frecuencia_respiratoria=limite + 1)
    assert resultado.nivel == 'amarillo' and 'A01' in ids(resultado)


def test_taquipnea_entre_2_y_3_meses_no_se_interpreta():
    resultado = evaluar(2, frecuencia_respiratoria=80)
    assert 'A01' not in ids(resultado)
    assert any('entre 2 y 3 meses' in aviso for aviso in resultado.avisos)


def test_tiraje_con_taquipnea_es_rojo():
    assert evaluar(18, frecuencia_respiratoria=55, tiraje_subcostal=True).nivel == 'rojo'


# ---------------------------------------------------------------- Hipoxemia según altitud (R07)

@pytest.mark.parametrize('altitud,umbral', [(0, 94), (1500, 94), (1501, 92), (2000, 92), (2001, 90),
                                            (2600, 88), (3000, 88), (3500, 83), (4000, 83)])
def test_hipoxemia_por_altitud(altitud, umbral):
    assert evaluar(spo2=umbral + 1, altitud_msnm=altitud).nivel == 'verde'
    assert 'R07' in ids(evaluar(spo2=umbral, altitud_msnm=altitud))     # la fuente dice "≤"


@pytest.mark.parametrize('altitud', [3200, 4500])
def test_hipoxemia_en_altitudes_sin_umbral_en_la_fuente(altitud):
    resultado = evaluar(spo2=70, altitud_msnm=altitud)
    assert 'R07' not in ids(resultado)
    assert any('no especifica el valor de saturación' in aviso for aviso in resultado.avisos)


def test_saturacion_sin_altitud_no_se_interpreta():
    resultado = evaluar(spo2=80)
    assert 'R07' not in ids(resultado)
    assert any('sin la altitud' in aviso for aviso in resultado.avisos)


# ---------------------------------------------------------------- Tos ferina (R16 / A02)

def test_tos_ferina_menor_de_3_meses_con_un_signo():
    resultado = evaluar(2, tos=True, vomito_tras_tos=True)
    assert resultado.nivel == 'rojo' and 'R16' in ids(resultado)


def test_tos_ferina_menor_de_6_meses_es_rojo_y_mayor_es_amarillo():
    cuadro = dict(tos=True, tos_paroxistica=True, estridor=True)
    assert 'R16' in ids(evaluar(5, **cuadro))
    resultado = evaluar(6, **cuadro)
    assert 'A02' in ids(resultado) and 'R16' not in ids(resultado)


def test_tos_ferina_por_tos_prolongada_requiere_mas_de_7_dias():
    assert 'A02' not in ids(evaluar(24, tos=True, dias_tos=7, tos_paroxistica=True))
    assert 'A02' in ids(evaluar(24, tos=True, dias_tos=8, tos_paroxistica=True))


def test_accesos_de_tos_sin_otros_criterios_no_son_caso_probable():
    assert 'A02' not in ids(evaluar(24, tos=True, tos_paroxistica=True, dias_tos=3))


# ---------------------------------------------------------------- Bronquiolitis (R17 / A08)

def test_sibilancias_en_menor_de_2_anios():
    assert evaluar(10, sibilancias=True).nivel == 'amarillo'
    assert 'R17' in ids(evaluar(1, sibilancias=True))                         # menor de 2 meses
    assert 'R17' in ids(evaluar(10, sibilancias=True, factor_riesgo_bar=True))
    assert evaluar(30, sibilancias=True).nivel == 'verde'                     # la fuente lo define para <2 años


# ---------------------------------------------------------------- Consultar (A03-A07)

@pytest.mark.parametrize('datos,regla', [
    ({'tos': True, 'dias_tos': 16}, 'A03'), ({'dias_fiebre': 8}, 'A04'), ({'contacto_tuberculosis': True}, 'A05'),
    ({'perdida_peso': True}, 'A06'), ({'disminucion_actividad': True}, 'A07'),
])
def test_criterios_de_consulta_son_amarillo(datos, regla):
    resultado = evaluar(**datos)
    assert resultado.nivel == 'amarillo' and regla in ids(resultado)


def test_limites_de_duracion():
    assert 'A03' not in ids(evaluar(tos=True, dias_tos=15))
    assert 'A04' not in ids(evaluar(dias_fiebre=7))


# ---------------------------------------------------------------- Salvaguarda (S01)

def test_dificultad_respiratoria_sin_medir_activa_salvaguarda_marcada():
    resultado = evaluar(dificultad_respiratoria=True)
    assert resultado.nivel == 'amarillo'
    senal = resultado.senales[0]
    assert senal['regla_id'] == 'S01' and senal['origen'] == 'salvaguarda'


def test_salvaguarda_no_se_duplica_si_la_taquipnea_esta_medida():
    assert ids(evaluar(24, respiracion_rapida=True, frecuencia_respiratoria=50)) == {'A01'}


# ---------------------------------------------------------------- Integración y trazabilidad

def test_la_evaluacion_guarda_version_senales_y_avisos(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'), meses=18)
    login(client, 'ana@test.com')
    respuesta = client.post(f'/sintomas/nino/{nino.id}/nuevo', data={
        'tiraje_subcostal': 'y', 'tos': 'y', 'temperatura': '38.6', 'frecuencia_respiratoria': '52',
    })
    assert respuesta.status_code == 302

    evaluacion = Evaluacion.query.one()
    assert evaluacion.nivel_riesgo == 'rojo' and evaluacion.version_reglas == 'v1-aiepi'
    detalle = json.loads(evaluacion.senales_json)
    assert {s['regla_id'] for s in detalle['senales']} == {'R01', 'A01'}
    assert detalle['senales'][0]['fuente']['url'].startswith('https://herramientaclinicaprimerainfancia')
    assert detalle['avisos']

    html = client.get(respuesta.headers['Location']).get_data(as_text=True)
    assert 'Tiraje subcostal' in html and 'Módulo 6 · Neumonía' in html
    assert 'pendiente de validación por un profesional de salud' in html


def test_formulario_valida_coherencia(client, app):
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    for datos in ({'dias_tos': '3'}, {'spo2': '90'}, {'frecuencia_respiratoria': '999'}, {'temperatura': '50'}):
        assert client.post(f'/sintomas/nino/{nino.id}/nuevo', data=datos).status_code == 400
    assert Evaluacion.query.count() == 0


def test_motor_v0_sigue_disponible_por_configuracion(client, app):
    app.config['MOTOR_CLINICO_VERSION'] = 'v0-provisional'
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    client.post(f'/sintomas/nino/{nino.id}/nuevo', data={'dificultad_respiratoria': 'y'})
    evaluacion = Evaluacion.query.one()
    assert evaluacion.version_reglas == 'v0-provisional' and evaluacion.nivel_riesgo == 'rojo'


def test_produccion_exige_reglas_validadas(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'x' * 40)
    monkeypatch.setenv('DATABASE_URL', 'postgresql://x')
    monkeypatch.setenv('RATELIMIT_STORAGE_URI', 'redis://localhost:6379/0')
    monkeypatch.setenv('MAIL_SERVER', 'smtp.respirakids.test')
    monkeypatch.setenv('MAIL_DEFAULT_SENDER', 'RespiraKids <no-responder@respirakids.test>')
    monkeypatch.delenv('REGLAS_CLINICAS_VALIDADAS', raising=False)
    with pytest.raises(RuntimeError, match='no están validadas'):
        ProductionConfig.validar()
    monkeypatch.setenv('REGLAS_CLINICAS_VALIDADAS', 'v1-aiepi')
    ProductionConfig.validar()


def test_documento_existe_en_el_repositorio():
    assert os.path.exists(RUTA_DOCUMENTO)
