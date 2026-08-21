from flask import Blueprint

mensajes_bp = Blueprint('mensajes', __name__, url_prefix='/mensajes')

from app.mensajes import routes