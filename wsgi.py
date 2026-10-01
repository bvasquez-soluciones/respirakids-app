"""Punto de entrada WSGI para producción.

    RESPIRAKIDS_ENV=production gunicorn --workers 3 --bind 127.0.0.1:8000 wsgi:app
"""
from app import create_app

app = create_app()
