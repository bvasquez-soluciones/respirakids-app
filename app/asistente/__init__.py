from flask import Blueprint

asistente_bp = Blueprint('asistente', __name__, url_prefix='/asistente')

from app.asistente import routes