from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    from app import models

    from app.auth import auth_bp
    app.register_blueprint(auth_bp)

    from app.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)

    from app.pacientes import pacientes_bp
    app.register_blueprint(pacientes_bp)

    from app.sintomas import sintomas_bp
    app.register_blueprint(sintomas_bp)

    from app.mensajes import mensajes_bp
    app.register_blueprint(mensajes_bp)

    from app.asistente import asistente_bp
    app.register_blueprint(asistente_bp)

    @app.route('/')
    def home():
        return render_template('home.html')

    return app

from app.models import Cuidador, Profesional

@login_manager.user_loader
def load_user(user_id):
    try:
        tipo, id_real = user_id.split('-')
        if tipo == 'cuidador':
            return Cuidador.query.get(int(id_real))
        elif tipo == 'profesional':
            return Profesional.query.get(int(id_real))
    except (ValueError, AttributeError):
        pass
    return None