from flask import Blueprint

pacientes_bp = Blueprint('pacientes', __name__, url_prefix='/pacientes')

from app.pacientes import routes