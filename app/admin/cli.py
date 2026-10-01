"""Comandos de administración (p. ej. crear el primer administrador en un servidor nuevo)."""
import click
from flask.cli import AppGroup

from app import db
from app.forms import password_segura, MENSAJE_PASSWORD
from app.models import Cuidador, Profesional

admin_cli = AppGroup('admin', help='Administración de RespiraKids.')


class _Campo:
    def __init__(self, data):
        self.data = data


@admin_cli.command('crear')
@click.option('--correo', prompt='Correo del administrador')
@click.option('--nombre', prompt='Nombres')
@click.option('--apellido', prompt='Apellidos')
@click.password_option('--password', prompt='Contraseña', confirmation_prompt='Confirma la contraseña')
def crear(correo, nombre, apellido, password):
    """Crea una cuenta de administrador (la contraseña no queda en el historial de la terminal)."""
    correo = correo.strip().lower()
    if Cuidador.query.filter_by(correo=correo).first() or Profesional.query.filter_by(correo=correo).first():
        raise click.ClickException('Ya existe una cuenta con ese correo.')
    try:
        password_segura(None, _Campo(password))
    except Exception:
        raise click.ClickException(MENSAJE_PASSWORD)
    admin = Cuidador(nombre=nombre.strip(), apellido=apellido.strip(), correo=correo, rol='admin')
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    click.echo(f'Administrador creado: {correo}. Al ingresar deberá aceptar la política de datos.')
