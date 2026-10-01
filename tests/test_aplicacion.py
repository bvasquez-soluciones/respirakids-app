import pytest

from config import ProductionConfig
from tests.conftest import crear_cuidador, login


def test_paginas_publicas(client):
    assert client.get('/').status_code == 200
    assert client.get('/auth/login').status_code == 200
    assert client.get('/auth/registro').status_code == 200


def test_pagina_404_propia(client):
    respuesta = client.get('/no-existe')
    assert respuesta.status_code == 404
    assert 'Página no encontrada' in respuesta.get_data(as_text=True)


def test_produccion_exige_secretos(monkeypatch):
    monkeypatch.delenv('SECRET_KEY', raising=False)
    monkeypatch.setenv('DATABASE_URL', 'postgresql://x')
    with pytest.raises(RuntimeError):
        ProductionConfig.validar()
    monkeypatch.setenv('SECRET_KEY', 'corta')
    with pytest.raises(RuntimeError):
        ProductionConfig.validar()


def test_asistente_valida_entrada(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    assert client.post('/asistente/preguntar', data='no-json').status_code == 400
    assert client.post('/asistente/preguntar', json={'pregunta': ''}).status_code == 400
    assert client.post('/asistente/preguntar', json={'pregunta': 'x' * 1001}).status_code == 400
    # Sin base de conocimiento ni API key responde de forma controlada, sin error 500.
    respuesta = client.post('/asistente/preguntar', json={'pregunta': '¿Cómo prevenir la gripa?'})
    assert respuesta.status_code == 200
    assert 'NO DISPONIBLE EN LA FUENTE CONSULTADA' in respuesta.get_json()['respuesta']
