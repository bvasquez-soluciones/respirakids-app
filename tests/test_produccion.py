"""Preparación para producción: chequeo de salud, trazabilidad de peticiones y configuración segura."""
import os

import pytest

from config import ProductionConfig, TestingConfig
from tests.conftest import crear_cuidador, login

ENTORNO_VALIDO = {
    'SECRET_KEY': 'x' * 40, 'DATABASE_URL': 'postgresql://u:p@localhost/db',
    'RATELIMIT_STORAGE_URI': 'redis://localhost:6379/0', 'REGLAS_CLINICAS_VALIDADAS': 'v1-aiepi',
    'MAIL_SERVER': 'smtp.respirakids.test', 'MAIL_DEFAULT_SENDER': 'RespiraKids <no-responder@respirakids.test>',
}


def test_chequeo_de_salud_sin_sesion(client, app):
    respuesta = client.get('/salud')
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {'estado': 'ok', 'base_de_datos': 'ok'}


def test_chequeo_de_salud_no_exige_politica_ni_sesion(client, app):
    crear_cuidador('ana@test.com', acepta_politica=False)
    login(client, 'ana@test.com')
    assert client.get('/salud').status_code == 200


def test_chequeo_de_salud_informa_caida_de_base_de_datos(client, app, monkeypatch):
    from app import db

    def fallar(*args, **kwargs):
        raise RuntimeError('sin conexión')
    monkeypatch.setattr(db.session, 'execute', fallar)
    assert client.get('/salud').status_code == 503


def test_cada_respuesta_lleva_id_de_peticion(client, app):
    generado = client.get('/').headers['X-Request-ID']
    assert len(generado) == 32
    assert client.get('/', headers={'X-Request-ID': 'abc12345-nginx'}).headers['X-Request-ID'] == 'abc12345-nginx'
    # Un id con caracteres no permitidos se reemplaza (evita inyectar texto en los logs).
    malicioso = 'abc"<script>alert(1)</script>'
    assert client.get('/', headers={'X-Request-ID': malicioso}).headers['X-Request-ID'] != malicioso


def test_produccion_arranca_con_configuracion_completa(monkeypatch):
    for clave, valor in ENTORNO_VALIDO.items():
        monkeypatch.setenv(clave, valor)
    ProductionConfig.validar()


@pytest.mark.parametrize('variable,valor,mensaje', [
    ('RATELIMIT_STORAGE_URI', 'memory://', 'Redis'),
    ('SECRET_KEY', 'corta', '32 caracteres'),
    ('REGLAS_CLINICAS_VALIDADAS', '', 'no están validadas'),
    ('MAIL_SERVER', '', 'MAIL_SERVER'),
])
def test_produccion_rechaza_configuracion_insegura(monkeypatch, variable, valor, mensaje):
    for clave, v in ENTORNO_VALIDO.items():
        monkeypatch.setenv(clave, v)
    monkeypatch.setenv(variable, valor)
    with pytest.raises(RuntimeError, match=mensaje):
        ProductionConfig.validar()


def test_cookies_de_produccion_son_seguras():
    assert ProductionConfig.SESSION_COOKIE_SECURE and ProductionConfig.REMEMBER_COOKIE_SECURE
    assert ProductionConfig.SESSION_COOKIE_HTTPONLY and ProductionConfig.FORCE_HTTPS
    assert ProductionConfig.SESSION_COOKIE_NAME.startswith('__Host-')
    assert ProductionConfig.ML_HABILITADO is False or os.environ.get('ML_HABILITADO') == 'true'


def test_archivos_de_despliegue_existen_con_finales_de_linea_lf():
    for ruta in ('gunicorn.conf.py', 'wsgi.py', 'deploy/nginx/respirakids.conf', 'deploy/systemd/respirakids.service',
                 'deploy/scripts/respaldo.sh', 'deploy/scripts/restaurar.sh', 'deploy/scripts/actualizar.sh',
                 '.github/workflows/ci.yml', 'docs/DESPLIEGUE.md'):
        with open(ruta, 'rb') as archivo:
            assert b'\r\n' not in archivo.read(), f'{ruta} tiene saltos de línea CRLF'


def test_produccion_redirige_http_a_https(monkeypatch):
    for clave, valor in ENTORNO_VALIDO.items():
        monkeypatch.setenv(clave, valor)
    # La configuración lee el entorno al importarse: se aplican la clave válida y la base de pruebas
    # (nunca la real ni la del .env).
    monkeypatch.setattr(ProductionConfig, 'SECRET_KEY', ENTORNO_VALIDO['SECRET_KEY'])
    monkeypatch.setattr(ProductionConfig, 'SQLALCHEMY_DATABASE_URI', TestingConfig.SQLALCHEMY_DATABASE_URI)
    monkeypatch.setattr(ProductionConfig, 'SQLALCHEMY_ENGINE_OPTIONS', TestingConfig.SQLALCHEMY_ENGINE_OPTIONS)
    from app import create_app
    cliente = create_app('production').test_client()
    respuesta = cliente.get('/auth/login', base_url='http://respirakids.test')
    assert respuesta.status_code == 302 and respuesta.headers['Location'].startswith('https://')
    # Detrás de Nginx la petición llega marcada como HTTPS y se atiende normalmente.
    assert cliente.get('/auth/login', base_url='http://respirakids.test',
                       headers={'X-Forwarded-Proto': 'https'}).status_code == 200
