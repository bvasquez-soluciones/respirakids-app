from flask import current_app, redirect, render_template, url_for
from flask_login import current_user

from app.ayuda import ayuda_bp
from app.presentacion import EVOLUCION, NIVELES

# Manuales por tipo de usuario. Cada quien ve solo los suyos: al cuidador no le sirve el del profesional.
# `roles` usa el campo `rol` del usuario ('cuidador', 'admin' o 'profesional'); None = visitante sin sesión.
MANUALES = (
    {'clave': 'cuidadores', 'emoji': '📘', 'titulo': 'Manual para cuidadores', 'endpoint': 'ayuda.cuidadores',
     'descripcion': 'Registrar niños y síntomas, entender el semáforo, hablar con un profesional y cuidar tus datos.',
     'roles': {None, 'cuidador', 'admin'}},
    {'clave': 'profesionales', 'emoji': '📗', 'titulo': 'Manual para profesionales de salud',
     'endpoint': 'ayuda.profesionales',
     'descripcion': 'Panel de pacientes y semáforo, solicitudes de atención, mensajes, indicaciones y reportes.',
     'roles': {None, 'profesional'}},
    # Se publica aquí cuando esté listo: administradores -> roles {'admin'}
)


def manuales_para(usuario):
    """Manuales disponibles para el usuario actual (o para un visitante)."""
    rol = usuario.rol if usuario.is_authenticated else None
    return [m for m in MANUALES if rol in m['roles']]


@ayuda_bp.route('/')
def indice():
    manuales = manuales_para(current_user)
    # Con un solo manual no hace falta elegir: se abre directamente.
    if len(manuales) == 1:
        return redirect(url_for(manuales[0]['endpoint']))
    return render_template('ayuda/indice.html', manuales=manuales)


def _niveles():
    return [(n, NIVELES[n]) for n in ('rojo', 'amarillo', 'verde', 'neutro')]


@ayuda_bp.route('/cuidadores')
def cuidadores():
    return render_template('ayuda/cuidadores.html', ejemplo={'nombre': 'Sofía', 'sexo': 'F'}, niveles=_niveles(),
                           evolucion=EVOLUCION)


@ayuda_bp.route('/profesionales')
def profesionales():
    return render_template('ayuda/profesionales.html', ejemplo={'nombre': 'Mateo', 'sexo': 'M'}, niveles=_niveles(),
                           evolucion=EVOLUCION, cupo=current_app.config['CUPO_CASOS_POR_PROFESIONAL'])
