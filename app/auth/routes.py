from datetime import timedelta
from urllib.parse import urlsplit

from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db, limiter
from app.auth import auth_bp
from app.forms import LoginForm, RegistroForm
from app.models import Cuidador, Profesional, ahora_utc
from app.services.auditoria import registrar_seguridad
from app.services.consentimiento import aceptar_politica

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


def _buscar_usuario(correo):
    return Cuidador.query.filter_by(correo=correo).first() or Profesional.query.filter_by(correo=correo).first()


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

        flash('Cuenta creada correctamente. Ahora inicia sesión.', 'success')
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
    registrar_seguridad('logout')
    logout_user()
    session.clear()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('auth.login'))


# Rutas disponibles mientras un profesional no haya cambiado su contraseña temporal.
_LIBRES_CAMBIO_PASSWORD = {'static', 'dashboard.ajustes', 'auth.logout', 'privacidad.politica', 'privacidad.aceptar'}


@auth_bp.before_app_request
def exigir_cambio_de_password_temporal():
    if (current_user.is_authenticated and getattr(current_user, 'debe_cambiar_password', False)
            and request.endpoint not in _LIBRES_CAMBIO_PASSWORD):
        flash('Por seguridad, cambia la contraseña temporal antes de continuar.', 'warning')
        return redirect(url_for('dashboard.ajustes'))
    return None
