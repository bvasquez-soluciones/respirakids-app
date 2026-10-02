import logging
from datetime import date

from flask import Flask, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, current_user
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix

from config import obtener_config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
mail = Mail()

# Orígenes externos permitidos para recursos estáticos (Bootstrap, Chart.js, fuentes).
# Sin 'unsafe-inline': todo el JS y el CSS viven en /static (lo verifica tests/test_diseno.py).
CSP = {
    'default-src': "'self'",
    'script-src': ["'self'", 'https://cdn.jsdelivr.net'],
    'style-src': ["'self'", 'https://cdn.jsdelivr.net', 'https://fonts.googleapis.com'],
    'font-src': ["'self'", 'https://fonts.gstatic.com', 'https://cdn.jsdelivr.net'],
    'img-src': ["'self'", 'data:', 'blob:'],
    'media-src': ["'self'", 'blob:'],  # notas de voz (vista previa de la grabación antes de enviarla)
    'connect-src': "'self'",
    'frame-ancestors': "'none'",
    'form-action': "'self'",
    'base-uri': "'self'",
}


def create_app(nombre_config=None):
    app = Flask(__name__)
    app.config.from_object(obtener_config(nombre_config))

    _configurar_logging(app)

    if not app.debug and not app.testing:
        # Detrás de un reverse proxy (Nginx) para obtener la IP y el esquema reales.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)

    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Inicia sesión para continuar.'
    login_manager.login_message_category = 'info'
    login_manager.session_protection = 'strong'

    if app.config['TALISMAN_ENABLED']:
        Talisman(
            app,
            content_security_policy=CSP,
            force_https=app.config['FORCE_HTTPS'],
            strict_transport_security=app.config['FORCE_HTTPS'],
            session_cookie_secure=app.config['SESSION_COOKIE_SECURE'],
            # Solo la propia aplicación puede pedir el micrófono (notas de voz); el resto de sensores, bloqueados.
            permissions_policy={'microphone': '(self)', 'camera': '()', 'geolocation': '()', 'payment': '()'},
        )

    from app import models  # noqa: F401  (registra los modelos en SQLAlchemy)

    from app.auth import auth_bp
    from app.dashboard import dashboard_bp
    from app.pacientes import pacientes_bp
    from app.sintomas import sintomas_bp
    from app.mensajes import mensajes_bp
    from app.asistente import asistente_bp
    from app.privacidad import privacidad_bp
    from app.medicamentos import medicamentos_bp
    from app.admin import admin_bp
    from app.sistema import asignar_id_peticion, devolver_id_peticion, sistema_bp

    app.before_request(asignar_id_peticion)
    app.after_request(devolver_id_peticion)

    for bp in (auth_bp, dashboard_bp, pacientes_bp, sintomas_bp, mensajes_bp, asistente_bp, privacidad_bp,
               medicamentos_bp, admin_bp, sistema_bp):
        app.register_blueprint(bp)

    @app.route('/')
    def home():
        return render_template('home.html')

    from app.fechas import FILTROS
    from app.models import ahora_utc
    from app.forms import atributos_campo
    app.jinja_env.filters.update(FILTROS)
    from app.presentacion import (
        AVISO_NO_DIAGNOSTICO, EMOJIS_GRUPOS, EMOJIS_SINTOMAS, EVOLUCION, expresion_avatar, hallazgos_registrados,
        icono_nivel, nivel_info,
    )
    app.jinja_env.globals.update(
        hoy_iso=lambda: date.today().isoformat(),
        atributos_campo=atributos_campo,
        nivel_info=nivel_info,
        icono_nivel=icono_nivel,
        expresion_avatar=expresion_avatar,
        hallazgos_registrados=hallazgos_registrados,
        ahora_utc=ahora_utc,
        AVISO_NO_DIAGNOSTICO=AVISO_NO_DIAGNOSTICO,
        EVOLUCION=EVOLUCION,
        EMOJIS_SINTOMAS=EMOJIS_SINTOMAS,
        EMOJIS_GRUPOS=EMOJIS_GRUPOS,
    )

    @app.context_processor
    def inyectar_contadores():
        if not current_user.is_authenticated:
            return {'alertas_count': 0, 'notificaciones_count': 0, 'solicitudes_count': 0}
        from app.services.notificaciones import contadores
        datos = contadores(current_user)
        return {'alertas_count': datos['alertas'], 'notificaciones_count': datos['notificaciones'],
                'solicitudes_count': datos['solicitudes']}

    from app.admin.cli import admin_cli
    from app.asistente.conocimiento import conocimiento_cli
    from app.clinica.documentacion import reglas_cli
    from app.ml.cli import ml_cli
    from app.privacidad.cli import privacidad_cli
    app.cli.add_command(reglas_cli)
    app.cli.add_command(conocimiento_cli)
    app.cli.add_command(admin_cli)
    app.cli.add_command(ml_cli)
    app.cli.add_command(privacidad_cli)

    _registrar_manejadores_error(app)
    return app


def _configurar_logging(app):
    """Logs a la salida estándar (los recoge systemd/journald). Cada línea lleva el id de la petición."""
    from app.sistema import FiltroIdPeticion
    nivel = getattr(logging, str(app.config.get('LOG_LEVEL', 'INFO')).upper(), logging.INFO)
    handler = logging.StreamHandler()
    handler.addFilter(FiltroIdPeticion())
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [req=%(request_id)s] [%(name)s] %(message)s'))
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(nivel)


def _registrar_manejadores_error(app):
    mensajes = {
        400: ('Solicitud no válida', 'La solicitud no se pudo procesar. Revisa los datos e inténtalo de nuevo.'),
        403: ('Acceso no permitido', 'No tienes permiso para ver esta información.'),
        404: ('Página no encontrada', 'La página que buscas no existe o fue movida.'),
        413: ('Archivo demasiado grande', 'El archivo supera el tamaño máximo permitido.'),
        429: ('Demasiados intentos', 'Has realizado demasiadas solicitudes. Espera unos minutos e inténtalo de nuevo.'),
        500: ('Error interno', 'Ocurrió un error inesperado. Ya quedó registrado; inténtalo de nuevo más tarde.'),
    }

    def renderizar(codigo):
        titulo, detalle = mensajes[codigo]
        return render_template('errors/error.html', codigo=codigo, titulo=titulo, detalle=detalle), codigo

    for codigo in (400, 403, 404, 413, 429):
        app.register_error_handler(codigo, lambda e, c=codigo: renderizar(c))

    @app.errorhandler(CSRFError)
    def csrf_error(e):
        titulo, _ = mensajes[400]
        return render_template(
            'errors/error.html', codigo=400, titulo=titulo,
            detalle='El formulario expiró o no es válido. Recarga la página e inténtalo de nuevo.'
        ), 400

    @app.errorhandler(500)
    def error_interno(e):
        db.session.rollback()
        app.logger.exception('Error interno no controlado')
        return renderizar(500)


@login_manager.user_loader
def load_user(user_id):
    """Carga el usuario de la sesión: '<tipo>-<id>-<huella de la contraseña>'."""
    import hmac
    from app.models import Cuidador, Profesional
    try:
        tipo, id_real, huella = user_id.split('-', 2)
        id_real = int(id_real)
    except (ValueError, AttributeError):
        return None  # incluye sesiones con el formato anterior: se pide iniciar sesión de nuevo
    modelo = {'cuidador': Cuidador, 'profesional': Profesional}.get(tipo)
    usuario = db.session.get(modelo, id_real) if modelo else None
    # Tras un cambio de contraseña la huella no coincide: la sesión de otros dispositivos se cierra.
    if usuario is None or not hmac.compare_digest(huella, usuario.huella_sesion()):
        return None
    # Un profesional suspendido pierde la sesión inmediatamente.
    if tipo == 'profesional' and not usuario.aprobado:
        return None
    return usuario
