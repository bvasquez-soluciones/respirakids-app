"""Recuperación de contraseña y verificación de correo mediante enlaces de un solo uso.

- El enlace lleva un token aleatorio de 256 bits (secrets.token_urlsafe).
- En la base de datos solo se guarda su hash SHA-256 y su vencimiento: quien lea la base no puede usarlos.
- Al usarse, el token se borra. Pedir un enlace nuevo invalida el anterior.
- Restablecer la contraseña cambia la huella de sesión (UsuarioMixin.huella_sesion): se cierran todas las
  sesiones abiertas en otros dispositivos.
"""
import hashlib
import secrets
from datetime import timedelta

from flask import current_app, url_for

from app import db
from app.models import Cuidador, Profesional, ahora_utc
from app.services.correo import enviar

LONGITUD_MAXIMA_TOKEN = 100


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _nuevo_token():
    token = secrets.token_urlsafe(32)
    return token, _hash(token)


def buscar_usuario_por_correo(correo):
    return Cuidador.query.filter_by(correo=correo).first() or Profesional.query.filter_by(correo=correo).first()


# ---------------------------------------------------------------- Recuperación de contraseña

def enviar_enlace_recuperacion(usuario):
    token, token_hash = _nuevo_token()
    minutos = current_app.config['MINUTOS_ENLACE_RECUPERACION']
    usuario.token_recuperacion = token_hash
    usuario.token_recuperacion_expira = ahora_utc() + timedelta(minutes=minutos)
    db.session.commit()
    enlace = url_for('auth.restablecer', token=token, _external=True)
    return enviar(usuario.correo, 'Restablece tu contraseña - RespiraKids', 'recuperacion',
                  usuario=usuario, enlace=enlace, minutos=minutos)


def usuario_por_token_recuperacion(token):
    """Usuario dueño de un enlace de recuperación vigente, o None (inexistente, usado o vencido)."""
    if not token or len(token) > LONGITUD_MAXIMA_TOKEN:
        return None
    token_hash = _hash(token)
    for modelo in (Cuidador, Profesional):
        usuario = modelo.query.filter_by(token_recuperacion=token_hash).first()
        if usuario:
            vigente = usuario.token_recuperacion_expira and usuario.token_recuperacion_expira > ahora_utc()
            return usuario if vigente else None
    return None


def restablecer_password(usuario, nueva):
    usuario.set_password(nueva)
    usuario.token_recuperacion = None
    usuario.token_recuperacion_expira = None
    # Recuperar la cuenta por correo también la desbloquea y reemplaza cualquier contraseña temporal.
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    if hasattr(usuario, 'debe_cambiar_password'):
        usuario.debe_cambiar_password = False
    # Usar el enlace demuestra que la persona controla el correo.
    if isinstance(usuario, Cuidador):
        usuario.correo_verificado = True
    db.session.commit()


# ---------------------------------------------------------------- Verificación de correo (cuidadores)
# Los profesionales no la necesitan: su cuenta la crea o aprueba un administrador.

def enviar_enlace_verificacion(cuidador):
    token, token_hash = _nuevo_token()
    horas = current_app.config['HORAS_ENLACE_VERIFICACION']
    cuidador.token_verificacion = token_hash
    cuidador.token_verificacion_expira = ahora_utc() + timedelta(hours=horas)
    db.session.commit()
    enlace = url_for('auth.verificar_correo', token=token, _external=True)
    return enviar(cuidador.correo, 'Confirma tu correo - RespiraKids', 'verificacion',
                  usuario=cuidador, enlace=enlace, horas=horas)


def verificar_correo(token):
    """Marca como verificado el correo dueño del token. Devuelve el cuidador o None si no es válido."""
    if not token or len(token) > LONGITUD_MAXIMA_TOKEN:
        return None
    cuidador = Cuidador.query.filter_by(token_verificacion=_hash(token)).first()
    if not cuidador or not cuidador.token_verificacion_expira or cuidador.token_verificacion_expira <= ahora_utc():
        return None
    cuidador.correo_verificado = True
    cuidador.token_verificacion = None
    cuidador.token_verificacion_expira = None
    db.session.commit()
    return cuidador
