from flask import render_template, request, jsonify, session
from flask_login import login_required, current_user
from app.asistente import asistente_bp
from app.asistente_ia import preguntar_asistente


@asistente_bp.route('/')
@login_required
def chat():
    session.pop('historial_asistente', None)
    return render_template('asistente/chat.html')


@asistente_bp.route('/preguntar', methods=['POST'])
@login_required
def preguntar():
    pregunta = request.json.get('pregunta', '').strip()

    if not pregunta:
        return jsonify({'error': 'Escribe una pregunta.'}), 400

    historial = session.get('historial_asistente', [])

    respuesta = preguntar_asistente(pregunta, historial)

    historial.append({"role": "user", "content": pregunta})
    historial.append({"role": "assistant", "content": respuesta})
    session['historial_asistente'] = historial[-10:]  # solo guardamos los últimos 10 mensajes

    return jsonify({'respuesta': respuesta})