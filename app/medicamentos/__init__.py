from flask import Blueprint

medicamentos_bp = Blueprint('medicamentos', __name__, url_prefix='/medicamentos')

from app.medicamentos import routes  # noqa: E402,F401
