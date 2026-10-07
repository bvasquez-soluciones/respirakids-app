from datetime import date, timedelta

import pytest

from app import create_app, db
from app.models import Autorizacion, Consentimiento, Cuidador, Nino, PatologiaBase, Profesional, ahora_utc
from app.models.privacidad import POLITICA_DATOS, TERMINOS_USO

PASSWORD = 'Clave1234'


@pytest.fixture
def app(tmp_path):
    app = create_app('testing')
    app.config['ADJUNTOS_FOLDER'] = str(tmp_path / 'adjuntos')  # cada prueba con su carpeta temporal
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def aceptar_politica(usuario, version=None):
    """Simula la aceptación de la política (versión indicada o vigente) y de los términos de uso vigentes."""
    from flask import current_app
    db.session.add(Consentimiento(
        usuario_id=usuario.id, usuario_tipo=usuario.tipo_usuario, tipo=POLITICA_DATOS, otorgado=True,
        version_politica=version or current_app.config['POLITICA_VERSION'],
    ))
    db.session.add(Consentimiento(
        usuario_id=usuario.id, usuario_tipo=usuario.tipo_usuario, tipo=TERMINOS_USO, otorgado=True,
        version_politica=current_app.config['TERMINOS_VERSION'],
    ))
    db.session.commit()


def crear_cuidador(correo='ana@test.com', rol='cuidador', acepta_politica=True):
    cuidador = Cuidador(nombre='Ana', correo=correo, rol=rol)
    cuidador.set_password(PASSWORD)
    db.session.add(cuidador)
    db.session.commit()
    if acepta_politica:
        aceptar_politica(cuidador)
    return cuidador


def crear_profesional(correo='dra@test.com', estado='aprobado', acepta_politica=True):
    profesional = Profesional(nombre='Laura', correo=correo, rol='profesional', estado_aprobacion=estado)
    profesional.set_password(PASSWORD)
    db.session.add(profesional)
    db.session.commit()
    if acepta_politica:
        aceptar_politica(profesional)
    return profesional


def crear_nino(cuidador, nombre='Sofía', meses=18, estado='activo', consentimiento=True):
    nino = Nino(
        nombre=nombre, sexo='F', cuidador_id=cuidador.id, estado=estado,
        fecha_nacimiento=date.today() - timedelta(days=int(meses * 30.5)),
        consentimiento_otorgado=consentimiento,
        consentimiento_fecha=ahora_utc() if consentimiento else None,
    )
    db.session.add(nino)
    db.session.commit()
    return nino


def autorizar(nino, profesional, **kwargs):
    autorizacion = Autorizacion(nino_id=nino.id, profesional_id=profesional.id, activa=True, **kwargs)
    db.session.add(autorizacion)
    db.session.commit()
    return autorizacion


def crear_patologia(nino, nombre='Asma'):
    patologia = PatologiaBase(nino_id=nino.id, nombre=nombre, activa=True)
    db.session.add(patologia)
    db.session.commit()
    return patologia


def login(client, correo, password=PASSWORD):
    return client.post('/auth/login', data={'correo': correo, 'password': password})
