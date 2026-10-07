"""Videollamadas de telemedicina entre el profesional que atiende un caso y el cuidador."""
from flask import Blueprint

videollamadas_bp = Blueprint('videollamadas', __name__, url_prefix='/videollamada')

from app.videollamadas import routes  # noqa: E402,F401
