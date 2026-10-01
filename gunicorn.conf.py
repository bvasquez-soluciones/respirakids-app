"""Configuración de Gunicorn para producción (se lee automáticamente desde la raíz del proyecto).

    RESPIRAKIDS_ENV=production gunicorn wsgi:app

Valores ajustables con variables de entorno: GUNICORN_BIND, GUNICORN_WORKERS, GUNICORN_TIMEOUT.
"""
import multiprocessing
import os

# Solo escucha en local: Nginx es quien atiende Internet y termina HTTPS.
bind = os.environ.get('GUNICORN_BIND', '127.0.0.1:8000')
workers = int(os.environ.get('GUNICORN_WORKERS', min(multiprocessing.cpu_count() * 2 + 1, 5)))
worker_class = 'sync'
timeout = int(os.environ.get('GUNICORN_TIMEOUT', 60))   # el asistente IA puede tardar algunos segundos
graceful_timeout = 30
keepalive = 5

# Reinicia cada proceso tras N peticiones para contener posibles fugas de memoria.
max_requests = 1000
max_requests_jitter = 100

# Solo se confía en las cabeceras X-Forwarded-* que llegan desde Nginx en la misma máquina.
forwarded_allow_ips = '127.0.0.1'

# Logs a la salida estándar (los recoge journald). El access log incluye el id de petición de Nginx.
accesslog = '-'
errorlog = '-'
loglevel = os.environ.get('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(M)sms req=%({x-request-id}i)s'

# Carga la aplicación antes de crear los procesos: un error de configuración impide arrancar desde el inicio.
preload_app = True
