from flask import Blueprint

privacidad_bp = Blueprint('privacidad', __name__, url_prefix='/privacidad')

from app.privacidad import routes  # noqa: E402,F401
