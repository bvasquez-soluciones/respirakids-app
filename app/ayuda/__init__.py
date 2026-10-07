"""Centro de ayuda: manuales de uso por tipo de usuario (públicos, también antes de crear una cuenta)."""
from flask import Blueprint

ayuda_bp = Blueprint('ayuda', __name__, url_prefix='/ayuda')

from app.ayuda import routes  # noqa: E402,F401
