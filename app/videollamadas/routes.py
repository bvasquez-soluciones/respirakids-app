import json

from flask import abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db, limiter
from app.models import SolicitudAtencion, Videollamada
from app.services import videollamadas as servicio
from app.services.acceso import es_profesional
from app.services.auditoria import registrar_seguridad
from app.services.notificaciones import marcar_leidas_de
from app.videollamadas import videollamadas_bp


def _rol():
    return 'profesional' if es_profesional() else 'cuidador'


def _llamada_propia(videollamada_id):
    """La llamada solo existe para sus dos participantes; para cualquier otra persona, 404."""
    llamada = db.session.get(Videollamada, videollamada_id)
    propia = llamada is not None and (
        llamada.profesional_id == current_user.id if es_profesional() else llamada.cuidador_id == current_user.id)
    if not propia:
        registrar_seguridad('acceso_denegado', descripcion=f'videollamada_id={videollamada_id}')
        abort(404)
    servicio.actualizar_vencida(llamada)
    return llamada


def _volver(llamada):
    if es_profesional():
        return url_for('mensajes.conversacion', nino_id=llamada.nino_id)
    return url_for('mensajes.hilo', nino_id=llamada.nino_id, profesional_id=llamada.profesional_id)


@videollamadas_bp.route('/caso/<int:solicitud_id>/iniciar', methods=['POST'])
@login_required
@limiter.limit('10 per minute')
def iniciar(solicitud_id):
    if not es_profesional():
        abort(404)
    solicitud = db.session.get(SolicitudAtencion, solicitud_id)
    if solicitud is None or solicitud.profesional_id != current_user.id:
        registrar_seguridad('acceso_denegado', descripcion=f'videollamada caso={solicitud_id}')
        abort(404)
    try:
        llamada = servicio.iniciar(solicitud, current_user._get_current_object())
    except servicio.VideollamadaNoPermitida as error:
        flash(str(error), 'warning')
        return redirect(url_for('mensajes.conversacion', nino_id=solicitud.nino_id))
    return redirect(url_for('videollamadas.sala', videollamada_id=llamada.id))


@videollamadas_bp.route('/<int:videollamada_id>')
@login_required
def sala(videollamada_id):
    llamada = _llamada_propia(videollamada_id)
    if not es_profesional():
        marcar_leidas_de(current_user, 'videollamada', llamada.id)
    return render_template(
        'videollamadas/sala.html', llamada=llamada, rol=_rol(), volver=_volver(llamada),
        ice=json.dumps(servicio.servidores_ice(f'{_rol()}-{current_user.id}')),
    )


@videollamadas_bp.route('/<int:videollamada_id>/responder', methods=['POST'])
@login_required
def responder(videollamada_id):
    if es_profesional():
        abort(404)
    llamada = _llamada_propia(videollamada_id)
    acepta = request.form.get('respuesta') == 'aceptar'
    try:
        servicio.responder(llamada, acepta, consentimiento=request.form.get('consentimiento') == 'si')
    except servicio.VideollamadaNoPermitida as error:
        flash(str(error), 'warning')
        return redirect(url_for('videollamadas.sala', videollamada_id=llamada.id))
    if not acepta:
        flash('Rechazaste la videollamada. Puedes seguir la conversación por mensajes.', 'info')
        return redirect(_volver(llamada))
    return redirect(url_for('videollamadas.sala', videollamada_id=llamada.id))


@videollamadas_bp.route('/<int:videollamada_id>/estado')
@login_required
def estado(videollamada_id):
    """Estado de la llamada y señales nuevas de la otra parte (static/js/videollamada.js lo consulta seguido)."""
    llamada = _llamada_propia(videollamada_id)
    rol = _rol()
    servicio.latido(llamada, rol)
    senales = servicio.senales_para(llamada, rol, request.args.get('desde', 0, type=int)) if llamada.activa else []
    return jsonify({
        'estado': llamada.estado,
        'duracion': llamada.duracion_segundos,
        'senales': [{'id': s.id, 'tipo': s.tipo, 'datos': json.loads(s.datos)} for s in senales],
    })


@videollamadas_bp.route('/<int:videollamada_id>/senal', methods=['POST'])
@login_required
@limiter.limit('240 per minute')
def senal(videollamada_id):
    llamada = _llamada_propia(videollamada_id)
    cuerpo = request.get_json(silent=True) or {}
    try:
        nueva = servicio.agregar_senal(llamada, _rol(), cuerpo.get('tipo'), cuerpo.get('datos'))
    except servicio.VideollamadaNoPermitida:
        return jsonify({'estado': llamada.estado}), 409
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    return jsonify({'id': nueva.id}), 201


@videollamadas_bp.route('/<int:videollamada_id>/colgar', methods=['POST'])
@login_required
def colgar(videollamada_id):
    llamada = _llamada_propia(videollamada_id)
    servicio.colgar(llamada, _rol())
    if request.accept_mimetypes.best == 'application/json' or request.is_json:
        return jsonify({'estado': llamada.estado})
    return redirect(_volver(llamada))
