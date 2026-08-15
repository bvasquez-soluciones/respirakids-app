from flask import Flask

def create_app():
    app = Flask(__name__)

    @app.route('/')
    def home():
        return '<h1>RespiraKids</h1><p>Aplicación en construcción 🚧</p>'

    return app