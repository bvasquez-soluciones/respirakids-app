from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
from dotenv import load_dotenv  # <-- 1. Importar load_dotenv

# Cargar las variables del archivo .env en el entorno
load_dotenv()                   # <-- 2. Cargar .env

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Asegurar que GEMINI_API_KEY se guarde explícitamente en la app config
    app.config['GEMINI_API_KEY'] = Config.GEMINI_API_KEY  # <-- 3. Cargar la clave

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
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

    @app.context_processor
    def inyectar_alertas_count():
        from flask_login import current_user
        if current_user.is_authenticated and current_user.rol == 'profesional':
            from app.models import Autorizacion
            autorizaciones = Autorizacion.query.filter_by(profesional_id=current_user.id, activa=True).all()
            count = 0
            for a in autorizaciones:
                if a.nino.evaluaciones:
                    ultima = sorted(a.nino.evaluaciones, key=lambda e: e.fecha)[-1]
                    if ultima.nivel_riesgo == 'rojo':
                        count += 1
            return {'alertas_count': count}
        return {'alertas_count': 0}

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