from flask import Blueprint

sintomas_bp = Blueprint('sintomas', __name__, url_prefix='/sintomas')

from app.sintomas import routes