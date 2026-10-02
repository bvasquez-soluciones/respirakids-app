"""Configuración por entorno de RespiraKids.

El entorno se elige con la variable RESPIRAKIDS_ENV: 'development' (por defecto),
'testing' o 'production'. Los secretos SIEMPRE vienen de variables de entorno.
"""
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}

    # Sesión y cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Formularios
    WTF_CSRF_TIME_LIMIT = None  # el token vive lo que dure la sesión

    # Archivos subidos (fuera de git, ver .gitignore)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    # Adjuntos de los mensajes (datos de salud): carpeta PRIVADA, fuera de /static y de git.
    ADJUNTOS_FOLDER = os.environ.get('ADJUNTOS_FOLDER', os.path.join(BASE_DIR, 'datos', 'adjuntos'))
    ADJUNTO_MAX_MB = 5  # igual que MAX_CONTENT_LENGTH y client_max_body_size de Nginx

    # Seguridad de cuentas
    MAX_INTENTOS_LOGIN = 5
    MINUTOS_BLOQUEO = 15
    # Vigencia de los enlaces enviados por correo (de un solo uso; se guardan solo como hash SHA-256).
    MINUTOS_ENLACE_RECUPERACION = 60
    HORAS_ENLACE_VERIFICACION = 48

    # Correo saliente (Flask-Mail): recuperación de contraseña y verificación de correo.
    # Sin MAIL_SERVER (solo desarrollo) los correos no se envían: se registran en el log.
    MAIL_SERVER = os.environ.get('MAIL_SERVER', '')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or None
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') or None
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'RespiraKids <no-responder@localhost>')
    MAIL_TIMEOUT = 10

    # Límite de peticiones (Flask-Limiter)
    RATELIMIT_STORAGE_URI = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')
    RATELIMIT_HEADERS_ENABLED = True

    # Cabeceras de seguridad (Flask-Talisman)
    TALISMAN_ENABLED = True
    FORCE_HTTPS = False

    # Asistente IA
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '').strip()
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.6-flash')

    # Motor clínico: versión del conjunto de reglas con que se evalúan los nuevos registros.
    # 'v1-aiepi' (Herramienta Clínica MinSalud) o 'v0-provisional' (reglas del prototipo).
    MOTOR_CLINICO_VERSION = os.environ.get('MOTOR_CLINICO_VERSION', 'v1-aiepi')

    # Machine Learning complementario (datos sintéticos, sin validación clínica)
    ML_HABILITADO = os.environ.get('ML_HABILITADO', 'true').lower() == 'true'
    ML_RUTA_MODELO = os.path.join(BASE_DIR, 'app', 'ml_models', 'riesgo_v1.joblib')
    ML_RUTA_DATASET = os.path.join(BASE_DIR, 'ml', 'datos', 'dataset_sintetico_v1.csv')

    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    # Las fechas se guardan en UTC y se muestran en esta zona horaria.
    ZONA_HORARIA = os.environ.get('ZONA_HORARIA', 'America/Bogota')

    # Política de tratamiento de datos. Al cambiar la versión, todos los usuarios deben aceptarla de nuevo.
    POLITICA_VERSION = '2.1'
    POLITICA_FECHA = '2026-10-01'
    # Términos y condiciones de uso: también se aceptan de nuevo al cambiar la versión.
    TERMINOS_VERSION = '1.0'
    TERMINOS_FECHA = '2026-10-01'
    # Conservación: mientras la cuenta esté activa y hasta N años tras la última actividad (salvo deber legal).
    CONSERVACION_ANIOS_INACTIVIDAD = 2

    # Atención por mensajes: casos abiertos que puede tener cada profesional antes de dejar de recibir solicitudes.
    CUPO_CASOS_POR_PROFESIONAL = 15
    # Datos del responsable del tratamiento (Ley 1581 de 2012). Deben completarse antes de operar.
    RESPONSABLE_NOMBRE = os.environ.get('RESPONSABLE_NOMBRE', '[Razón social del responsable]')
    RESPONSABLE_ID = os.environ.get('RESPONSABLE_ID', '[NIT o documento]')
    RESPONSABLE_DIRECCION = os.environ.get('RESPONSABLE_DIRECCION', '[Dirección]')
    RESPONSABLE_CORREO = os.environ.get('RESPONSABLE_CORREO', '[correo de contacto para protección de datos]')
    RESPONSABLE_TELEFONO = os.environ.get('RESPONSABLE_TELEFONO', '[Teléfono]')


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = Config.SECRET_KEY or 'solo-desarrollo-no-usar-en-produccion'
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = 'clave-de-pruebas'
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite://')
    SQLALCHEMY_ENGINE_OPTIONS = {}
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    TALISMAN_ENABLED = False
    ML_HABILITADO = False
    GEMINI_API_KEY = ''
    MAIL_SERVER = 'localhost'
    MAIL_SUPPRESS_SEND = True  # Flask-Mail guarda los mensajes en un buzón de prueba


class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_NAME = '__Host-respirakids'   # solo HTTPS, sin dominio ni subrutas
    PREFERRED_URL_SCHEME = 'https'
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_size': 5, 'max_overflow': 5, 'pool_recycle': 1800}
    REMEMBER_COOKIE_SECURE = True
    FORCE_HTTPS = True
    # Hasta tener datos reales y validación, el ML queda apagado salvo que se active explícitamente.
    ML_HABILITADO = os.environ.get('ML_HABILITADO', 'false').lower() == 'true'

    @classmethod
    def validar(cls):
        # Sin correo saliente no hay recuperación de contraseña ni verificación de cuentas.
        faltantes = [v for v in ('SECRET_KEY', 'DATABASE_URL', 'MAIL_SERVER', 'MAIL_DEFAULT_SENDER')
                     if not os.environ.get(v)]
        if faltantes:
            raise RuntimeError(f'Faltan variables de entorno obligatorias en producción: {", ".join(faltantes)}')
        if len(os.environ['SECRET_KEY']) < 32:
            raise RuntimeError('SECRET_KEY debe tener al menos 32 caracteres en producción.')
        # Con varios procesos de Gunicorn el límite de peticiones en memoria no se comparte: se exige Redis.
        if not os.environ.get('RATELIMIT_STORAGE_URI', '').startswith(('redis://', 'rediss://')):
            raise RuntimeError('En producción RATELIMIT_STORAGE_URI debe apuntar a Redis (redis://...).')
        # Las reglas clínicas solo pueden usarse con pacientes reales cuando un profesional de salud
        # validó esa versión exacta (ver docs/REGLAS_CLINICAS_v1.md).
        version = os.environ.get('MOTOR_CLINICO_VERSION', 'v1-aiepi')
        if os.environ.get('REGLAS_CLINICAS_VALIDADAS') != version:
            raise RuntimeError(
                f'Las reglas clínicas {version} no están validadas por un profesional de salud. '
                f'Tras la validación documentada, define REGLAS_CLINICAS_VALIDADAS={version}.'
            )


CONFIGURACIONES = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}


def obtener_config(nombre=None):
    nombre = nombre or os.environ.get('RESPIRAKIDS_ENV', 'development')
    if nombre not in CONFIGURACIONES:
        raise RuntimeError(f'Entorno desconocido: {nombre!r}. Usa uno de: {", ".join(CONFIGURACIONES)}')
    config = CONFIGURACIONES[nombre]
    if hasattr(config, 'validar'):
        config.validar()
    return config
