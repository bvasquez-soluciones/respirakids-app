from flask import render_template

from app.ayuda import ayuda_bp
from app.presentacion import EVOLUCION, NIVELES


@ayuda_bp.route('/')
def indice():
    return render_template('ayuda/indice.html')


@ayuda_bp.route('/cuidadores')
def cuidadores():
    """Manual del cuidador. Los textos del semáforo y del seguimiento salen de app/presentacion.py (los mismos que
    muestra la aplicación), así el manual no se desactualiza."""
    ejemplo = {'nombre': 'Sofía', 'sexo': 'F'}  # niña de ejemplo para mostrar los avatares
    orden = ('rojo', 'amarillo', 'verde', 'neutro')
    return render_template('ayuda/cuidadores.html', ejemplo=ejemplo, niveles=[(n, NIVELES[n]) for n in orden],
                           evolucion=EVOLUCION)
