import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    modo_debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=modo_debug)