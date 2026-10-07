from datetime import timedelta
from urllib.parse import urlsplit

from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db, limiter
from app.auth import auth_bp
from app.forms import LoginForm, RecuperarPasswordForm, RegistroForm, RestablecerPasswordForm
from app.models import Cuidador, ahora_utc
from app.services.auditoria import registrar_seguridad
from app.services.consentimiento import aceptar_politica
from app.services.cuentas import (
    buscar_usuario_por_correo, enviar_enlace_recuperacion, enviar_enlace_verificacion, restablecer_password,
    usuario_por_token_recuperacion, verificar_correo as verificar_token_correo,
)

MENSAJE_CREDENCIALES = 'Correo o contraseña incorrectos.'


def _destino_inicial(usuario):
    if usuario.tipo_usuario == 'profesional':
        return url_for('dashboard.profesional')
    if usuario.rol == 'admin':
        return url_for('admin.inicio')
    return url_for('dashboard.cuidador')


def _siguiente_seguro():
    """Solo se permite redirigir a rutas internas (evita redirecciones abiertas)."""
    destino = request.args.get('next', '')
    partes = urlsplit(destino)
    if destino.startswith('/') and not destino.startswith('//') and not partes.netloc and not partes.scheme:
        return destino
    return None


_buscar_usuario = buscar_usuario_por_correo

# Mismo mensaje exista o no la cuenta: no se revela qué correos están registrados.
MENSAJE_RECUPERACION = ('Si el correo corresponde a una cuenta de RespiraKids, recibirás un enlace para restablecer '
                        'la contraseña. Revisa también la carpeta de correo no deseado.')


def _registrar_intento_fallido(usuario):
    usuario.intentos_fallidos = (usuario.intentos_fallidos or 0) + 1
    if usuario.intentos_fallidos >= current_app.config['MAX_INTENTOS_LOGIN']:
        usuario.bloqueado_hasta = ahora_utc() + timedelta(minutes=current_app.config['MINUTOS_BLOQUEO'])
        usuario.intentos_fallidos = 0
        db.session.commit()
        registrar_seguridad('cuenta_bloqueada', usuario=usuario)
    else:
        db.session.commit()
        registrar_seguridad('login_fallido', usuario=usuario)


@auth_bp.route('/registro', methods=['GET', 'POST'])
@limiter.limit('5 per minute', methods=['POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(_destino_inicial(current_user))

    form = RegistroForm()
    if request.method == 'POST':
        if not form.validate_on_submit():
            return render_template('auth/registro.html', form=form), 400

        if _buscar_usuario(form.correo.data):
            form.correo.errors.append('Ya existe una cuenta con ese correo. Si es tuya, inicia sesión.')
            return render_template('auth/registro.html', form=form), 400

        cuidador = Cuidador(
            nombre=form.nombre.data,
            apellido=form.apellido.data,
            correo=form.correo.data,
            telefono=form.telefono.data or None,
        )
        cuidador.set_password(form.password.data)
        db.session.add(cuidador)
        db.session.flush()
        aceptar_politica(cuidador)  # la cuenta y su autorización se guardan juntas
        db.session.commit()
        registrar_seguridad('registro_cuenta', usuario=cuidador)
        enviar_enlace_verificacion(cuidador)

        flash('Cuenta creada correctamente. Te enviamos un correo para confirmar tu dirección; '
              'ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/registro.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(_destino_inicial(current_user))

    form = LoginForm()
    if request.method == 'POST':
        if not form.validate_on_submit():
            return render_template('auth/login.html', form=form), 400

        usuario = _buscar_usuario(form.correo.data)

        if usuario and usuario.esta_bloqueado():
            registrar_seguridad('login_cuenta_bloqueada', usuario=usuario)
            flash('Tu cuenta está bloqueada temporalmente por varios intentos fallidos. '
                  'Inténtalo de nuevo más tarde.', 'danger')
            return render_template('auth/login.html', form=form), 403

        if not usuario or not usuario.check_password(form.password.data):
            if usuario:
                _registrar_intento_fallido(usuario)
            else:
                registrar_seguridad('login_fallido', descripcion='correo no registrado')
            flash(MENSAJE_CREDENCIALES, 'danger')
            return render_template('auth/login.html', form=form), 401

        if usuario.tipo_usuario == 'profesional' and not usuario.aprobado:
            registrar_seguridad('login_profesional_no_aprobado', usuario=usuario)
            flash('Tu cuenta profesional aún no ha sido aprobada.', 'warning')
            return render_template('auth/login.html', form=form), 403

        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = None
        db.session.commit()

        session.clear()  # evita fijación de sesión
        session.permanent = True
        login_user(usuario)
        registrar_seguridad('login_exitoso', usuario=usuario)
        flash('Bienvenido/a de nuevo.', 'success')
        return redirect(_siguiente_seguro() or _destino_inicial(usuario))

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    # Solo POST (con token CSRF) cierra la sesión: un enlace o imagen de otro sitio no puede cerrarla.
    if request.method == 'GET':
        return render_template('auth/logout.html')
    registrar_seguridad('logout')
    logout_user()
    session.clear()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('auth.login'))


# ---------------------------------------------------------------- Recuperación de contraseña

@auth_bp.route('/recuperar', methods=['GET', 'POST'])
@limiter.limit('5 per minute;20 per hour', methods=['POST'])
def recuperar():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.ajustes' if current_user.tipo_usuario == 'profesional'
                                else 'dashboard.perfil'))
    form = RecuperarPasswordForm()
    if request.method == 'POST':
        if not form.validate_on_submit():
            return render_template('auth/recuperar.html', form=form), 400
        usuario = _buscar_usuario(form.correo.data)
        # Profesionales pendientes o suspendidos no pueden recuperar el acceso por su cuenta.
        if usuario and (usuario.tipo_usuario != 'profesional' or usuario.aprobado):
            enviar_enlace_recuperacion(usuario)
            registrar_seguridad('recuperacion_solicitada', usuario=usuario)
        else:
            registrar_seguridad('recuperacion_solicitada', descripcion='correo sin cuenta habilitada')
        flash(MENSAJE_RECUPERACION, 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/recuperar.html', form=form)


@auth_bp.route('/restablecer/<token>', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
def restablecer(token):
    usuario = usuario_por_token_recuperacion(token)
    if usuario is None:
        registrar_seguridad('recuperacion_enlace_invalido')
        return render_template('auth/restablecer.html', form=None), 400

    form = RestablecerPasswordForm()
    if request.method == 'POST':
        if not form.validate_on_submit():
            return render_template('auth/restablecer.html', form=form), 400
        restablecer_password(usuario, form.password.data)
        registrar_seguridad('password_restablecida', usuario=usuario)
        logout_user()
        session.clear()
        flash('Tu contraseña se actualizó y se cerraron las sesiones abiertas. Inicia sesión con la nueva.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/restablecer.html', form=form)


# ---------------------------------------------------------------- Verificación de correo

@auth_bp.route('/verificar/<token>')
@limiter.limit('10 per minute')
def verificar_correo(token):
    cuidador = verificar_token_correo(token)
    if cuidador is None:
        registrar_seguridad('verificacion_enlace_invalido')
        flash('El enlace de confirmación no es válido o ya venció. Inicia sesión y solicita uno nuevo.', 'warning')
    else:
        registrar_seguridad('correo_verificado', usuario=cuidador)
        flash('¡Listo! Confirmaste tu correo.', 'success')
    destino = 'dashboard.cuidador' if current_user.is_authenticated else 'auth.login'
    return redirect(url_for(destino))


@auth_bp.route('/verificar/reenviar', methods=['POST'])
@login_required
@limiter.limit('3 per minute;10 per day')
def reenviar_verificacion():
    if isinstance(current_user._get_current_object(), Cuidador) and not current_user.correo_verificado:
        enviar_enlace_verificacion(current_user._get_current_object())
        registrar_seguridad('verificacion_reenviada')
        flash(f'Te enviamos un nuevo enlace de confirmación a {current_user.correo}.', 'info')
    return redirect(url_for('dashboard.cuidador'))


# Rutas disponibles mientras un profesional no haya cambiado su contraseña temporal.
_LIBRES_CAMBIO_PASSWORD = {'static', 'dashboard.ajustes', 'auth.logout', 'auth.restablecer', 'privacidad.politica',
                           'privacidad.aceptar', 'ayuda.indice', 'ayuda.profesionales'}


@auth_bp.before_app_request
def exigir_cambio_de_password_temporal():
    if (current_user.is_authenticated and getattr(current_user, 'debe_cambiar_password', False)
            and request.endpoint not in _LIBRES_CAMBIO_PASSWORD):
        flash('Por seguridad, cambia la contraseña temporal antes de continuar.', 'warning')
        return redirect(url_for('dashboard.ajustes'))
    return None
