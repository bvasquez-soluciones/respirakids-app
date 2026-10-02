"""Comandos de protección de datos.

    flask privacidad conservacion              # lista las cuentas que superaron el plazo de conservación
    flask privacidad conservacion --ejecutar   # las anonimiza (irreversible)

Plazo: CONSERVACION_ANIOS_INACTIVIDAD años sin actividad (último inicio de sesión o, si nunca ingresó, fecha de
registro). Se recomienda programarlo una vez al mes y revisar primero la lista sin --ejecutar.
"""
from datetime import timedelta

import click
from flask import current_app
from flask.cli import AppGroup
from sqlalchemy import func

from app import db
from app.models import Cuidador, LogSeguridad, Profesional, ahora_utc
from app.services.auditoria import registrar_seguridad
from app.services.supresion import anonimizar_cuidador, anonimizar_profesional, esta_anonimizado

privacidad_cli = AppGroup('privacidad', help='Protección de datos personales (Ley 1581 de 2012).')


def ultima_actividad(usuario):
    ultimo_login = (
        db.session.query(func.max(LogSeguridad.timestamp))
        .filter_by(usuario_tipo=usuario.tipo_usuario, usuario_id=usuario.id, evento='login_exitoso')
        .scalar()
    )
    return ultimo_login or usuario.fecha_registro


def cuentas_vencidas(anios):
    """Cuentas (no administradoras, no anonimizadas) sin actividad en los últimos `anios` años."""
    limite = ahora_utc() - timedelta(days=365 * anios)
    candidatos = [c for c in Cuidador.query.all() if c.rol != 'admin'] + Profesional.query.all()
    return [u for u in candidatos
            if not esta_anonimizado(u) and (ultima_actividad(u) or limite) < limite]


@privacidad_cli.command('conservacion')
@click.option('--ejecutar', is_flag=True, help='Anonimiza las cuentas listadas (irreversible).')
def conservacion(ejecutar):
    """Aplica el período de conservación de la política de tratamiento de datos."""
    anios = current_app.config['CONSERVACION_ANIOS_INACTIVIDAD']
    vencidas = cuentas_vencidas(anios)
    click.echo(f'Cuentas sin actividad hace más de {anios} años: {len(vencidas)}')
    for usuario in vencidas:  # solo identificadores internos: la salida puede quedar en logs
        click.echo(f'  - {usuario.tipo_usuario} #{usuario.id} (última actividad: {ultima_actividad(usuario):%Y-%m-%d})')
    if not ejecutar:
        if vencidas:
            click.echo('No se modificó nada. Para anonimizarlas ejecuta de nuevo con --ejecutar.')
        return
    for usuario in vencidas:
        (anonimizar_cuidador if isinstance(usuario, Cuidador) else anonimizar_profesional)(usuario)
        db.session.commit()
        registrar_seguridad('conservacion_anonimizacion',
                            descripcion=f'{usuario.tipo_usuario} #{usuario.id}: plazo de conservación cumplido')
    click.echo(f'Anonimizadas: {len(vencidas)}')
