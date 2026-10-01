"""Convenciones de formularios: obligatorios marcados, errores junto al campo y normalización de datos."""
import re
from datetime import date, timedelta

import pytest

from app.models import Cuidador, Nino
from tests.conftest import PASSWORD, crear_cuidador, login

REGISTRO_VALIDO = {
    'nombre': 'Ana María', 'apellido': 'Torres Gómez', 'correo': 'ana@test.com', 'telefono': '',
    'password': PASSWORD, 'confirmar_password': PASSWORD, 'acepta_politica': 'y',
}


def test_registro_marca_obligatorios_y_opcionales(client, app):
    html = client.get('/auth/registro').get_data(as_text=True)
    assert 'Los campos marcados con' in html
    for etiqueta in ('Nombres', 'Apellidos', 'Correo electrónico', 'Contraseña', 'Confirmar contraseña'):
        assert f'{etiqueta}<span class="rk-requerido" aria-hidden="true"> *</span>' in html, etiqueta
    assert 'Teléfono celular <span class="rk-opcional">(opcional)</span>' in html
    # La regla de la interfaz coincide con la del servidor: el navegador también exige los obligatorios.
    def atributos(campo):
        return re.search(rf'<input[^>]*id="{campo}"[^>]*>', html).group(0)

    assert ' required' in atributos('nombre') and ' required' in atributos('apellido')
    assert ' required' not in atributos('telefono')
    assert 'minlength="8"' in atributos('password')


@pytest.mark.parametrize('campo,valor,mensaje', [
    ('nombre', '', 'Este campo es obligatorio.'),
    ('apellido', '', 'Este campo es obligatorio.'),
    ('nombre', 'Ana123', 'Usa solo letras'),
    ('apellido', 'T', 'Debe tener entre 2 y 100 caracteres.'),
    ('correo', 'no-es-correo', 'Escribe un correo válido'),
    ('telefono', '12ab', 'Escribe un teléfono válido'),
    ('confirmar_password', 'OtraClave99', 'Las contraseñas no coinciden.'),
    ('acepta_politica', '', 'Debes aceptar la política'),
])
def test_registro_muestra_error_junto_al_campo(client, app, campo, valor, mensaje):
    datos = {**REGISTRO_VALIDO, campo: valor}
    if campo == 'acepta_politica':
        datos.pop('acepta_politica')
    respuesta = client.post('/auth/registro', data=datos)
    html = respuesta.get_data(as_text=True)

    assert respuesta.status_code == 400
    assert Cuidador.query.count() == 0
    assert f'id="{campo}-error"' in html and mensaje in html
    assert 'aria-invalid="true"' in html
    assert 'id="resumen-errores"' in html


def test_registro_conserva_lo_escrito_salvo_contrasenas(client, app):
    html = client.post('/auth/registro', data={**REGISTRO_VALIDO, 'apellido': ''}).get_data(as_text=True)
    assert 'value="Ana María"' in html and 'value="ana@test.com"' in html
    assert PASSWORD not in html


def test_registro_normaliza_espacios_y_correo(client, app):
    client.post('/auth/registro', data={
        **REGISTRO_VALIDO, 'nombre': '  Ana   María ', 'apellido': " O'Neil  Pérez-Gómez ", 'correo': ' ANA@Test.COM ',
    })
    cuidador = Cuidador.query.one()
    assert cuidador.nombre == 'Ana María'
    assert cuidador.apellido == "O'Neil Pérez-Gómez"
    assert cuidador.correo == 'ana@test.com'


def test_formulario_de_nino_exige_nombres_y_apellidos(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    html = client.get('/pacientes/nuevo').get_data(as_text=True)
    assert 'Apellidos<span class="rk-requerido"' in html
    assert 'Peso (kg) <span class="rk-opcional">(opcional)</span>' in html

    respuesta = client.post('/pacientes/nuevo', data={
        'nombre': 'Sofía', 'apellido': '', 'sexo': 'F', 'consentimiento_tratamiento': 'y',
        'fecha_nacimiento': (date.today() - timedelta(days=300)).isoformat(),
    })
    assert respuesta.status_code == 400
    assert 'id="apellido-error"' in respuesta.get_data(as_text=True)
    assert Nino.query.count() == 0


def test_autorizacion_de_profesional_inexistente_muestra_error_en_campo(client, app):
    from tests.conftest import crear_nino
    nino = crear_nino(crear_cuidador('ana@test.com'))
    login(client, 'ana@test.com')
    respuesta = client.post(f'/pacientes/{nino.id}/autorizaciones', data={'correo_profesional': 'nadie@test.com'})
    assert respuesta.status_code == 400
    assert 'No se encontró un profesional habilitado' in respuesta.get_data(as_text=True)


def test_cambio_de_password_muestra_errores_en_campo(client, app):
    crear_cuidador('ana@test.com')
    login(client, 'ana@test.com')
    respuesta = client.post('/dashboard/perfil', data={
        'accion': 'cambiar_password', 'password_actual': 'incorrecta1',
        'password_nueva': 'NuevaClave1', 'password_confirmar': 'NuevaClave1',
    })
    assert respuesta.status_code == 400
    assert 'La contraseña actual no es correcta.' in respuesta.get_data(as_text=True)
