"""Operación del servicio: chequeo de salud e identificador de petición para los logs."""
import logging
import re
import uuid

from flask import Blueprint, g, has_request_context, jsonify, request
from sqlalchemy import text

from app import db, limiter

sistema_bp = Blueprint('sistema', __name__)

_ID_VALIDO = re.compile(r'^[A-Za-z0-9\-]{8,64}$')


@sistema_bp.route('/salud')
@limiter.exempt
def salud():
    """Chequeo para el monitoreo y el proxy. No requiere sesión ni expone detalles internos."""
    try:
        db.session.execute(text('SELECT 1'))
        return jsonify(estado='ok', base_de_datos='ok'), 200
    except Exception:
        db.session.rollback()
        return jsonify(estado='error', base_de_datos='sin conexión'), 503


def asignar_id_peticion():
    """Usa el X-Request-ID que envía Nginx (si es válido) o genera uno nuevo."""
    recibido = request.headers.get('X-Request-ID', '')
    g.request_id = recibido if _ID_VALIDO.match(recibido) else uuid.uuid4().hex


def devolver_id_peticion(respuesta):
    if hasattr(g, 'request_id'):
        respuesta.headers['X-Request-ID'] = g.request_id
    return respuesta


class FiltroIdPeticion(logging.Filter):
    """Añade `request_id` a cada línea de log para poder seguir una petición de punta a punta."""

    def filter(self, registro):
        registro.request_id = getattr(g, 'request_id', '-') if has_request_context() else '-'
        return True
