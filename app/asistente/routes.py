import json

from flask import jsonify, render_template, request, session
from flask_login import current_user, login_required

from app import db, limiter
from app.asistente import asistente_bp
from app.asistente.servicio import responder
from app.models import ConsultaIA, Evaluacion
from app.presentacion import nivel_info
from app.services.acceso import es_cuidador, es_profesional
from app.services.anonimizacion import anonimizar
from app.services.auditoria import registrar_actividad
from app.services.resumen_nino import senales_de_evaluacion

MAX_LONGITUD_PREGUNTA = 1000
MAX_TURNOS_HISTORIAL = 6          # mensajes (pregunta + respuesta) que se conservan
MAX_LONGITUD_TURNO = 600          # caracteres por mensaje guardado en la sesión (cookie limitada a ~4 KB)


def _nombres_a_proteger():
    """Nombres del usuario y de sus niños/as, que nunca deben salir hacia el proveedor de IA."""
    nombres = [current_user.nombre, getattr(current_user, 'apellido', None)]
    for nino in getattr(current_user, 'ninos', []):
        nombres += [nino.nombre, nino.apellido]
    return nombres


def _contexto_de_evaluacion(evaluacion_id):
    """Señales (sin datos personales) de una evaluación del cuidador, para responder sobre ella."""
    evaluacion = db.session.get(Evaluacion, evaluacion_id) if evaluacion_id else None
    if not evaluacion or not es_cuidador() or evaluacion.nino.cuidador_id != current_user.id:
        return None
    return {
        'evaluacion_id': evaluacion.id,
        'nino_id': evaluacion.nino_id,
        'nivel': nivel_info(evaluacion.nivel_riesgo)['nombre'],
        'senales': [s['texto'] for s in senales_de_evaluacion(evaluacion)],
    }


@asistente_bp.route('/')
@login_required
def chat():
    session.pop('historial_asistente', None)
    contexto = _contexto_de_evaluacion(request.args.get('evaluacion', type=int))
    session['contexto_asistente'] = contexto
    return render_template('asistente/chat.html', contexto=contexto)


@asistente_bp.route('/preguntar', methods=['POST'])
@login_required
@limiter.limit('15 per minute; 200 per day')
def preguntar():
    datos = request.get_json(silent=True) or {}
    pregunta = str(datos.get('pregunta', '')).strip()

    if not pregunta:
        return jsonify({'error': 'Escribe una pregunta.'}), 400
    if len(pregunta) > MAX_LONGITUD_PREGUNTA:
        return jsonify({'error': f'La pregunta no puede superar {MAX_LONGITUD_PREGUNTA} caracteres.'}), 400

    pregunta = anonimizar(pregunta, _nombres_a_proteger())
    contexto = session.get('contexto_asistente')
    historial = session.get('historial_asistente', [])

    respuesta = responder(pregunta, es_profesional=es_profesional(), contexto=contexto, historial=historial)

    historial += [
        {'role': 'user', 'content': pregunta[:MAX_LONGITUD_TURNO]},
        {'role': 'assistant', 'content': respuesta.texto[:MAX_LONGITUD_TURNO]},
    ]
    session['historial_asistente'] = historial[-MAX_TURNOS_HISTORIAL:]
    _registrar_consulta(pregunta, respuesta, contexto)

    return jsonify(respuesta.como_dict())


def _registrar_consulta(pregunta_anonimizada, respuesta, contexto):
    """Trazabilidad: qué tipo de respuesta se dio y con qué fuentes (la pregunta se guarda anonimizada)."""
    fuentes = [f['titulo'] for f in respuesta.fuentes]
    if es_cuidador():
        db.session.add(ConsultaIA(
            cuidador_id=current_user.id,
            nino_id=contexto['nino_id'] if contexto else None,
            categoria_sintoma='alarma' if respuesta.alarma else None,
            contexto_json=json.dumps({'pregunta': pregunta_anonimizada,
                                      'evaluacion_id': contexto['evaluacion_id'] if contexto else None},
                                     ensure_ascii=False),
            resultado=respuesta.tipo,
            fuentes_citadas=json.dumps(fuentes, ensure_ascii=False),
        ))
        db.session.commit()
    else:
        registrar_actividad('consultar_asistente', 'asistente', None,
                            detalles={'tipo': respuesta.tipo, 'fuentes': fuentes})
