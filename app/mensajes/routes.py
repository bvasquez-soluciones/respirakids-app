"""Mensajería privada y atención por mensajes con los profesionales de la clínica.

Cada conversación es de un niño/a con UN profesional (`Mensaje.profesional_conversacion_id`):
- El cuidador ve una bandeja con una conversación por profesional; los demás profesionales no la ven.
- "Hablar con un profesional": la solicitud la reciben los profesionales disponibles con cupo y la atiende el
  primero que acepta (ver services/atencion.py). Luego el cuidador decide si le autoriza el expediente completo.
- Los mensajes antiguos del cuidador sin destinatario solo los ve el cuidador.
"""
from flask import abort, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required

from app import db, limiter
from app.decorators import rol_requerido
from app.forms import MensajeForm, SolicitudAtencionForm, primer_error
from app.mensajes import mensajes_bp
from app.models import AdjuntoMensaje, Autorizacion, Mensaje, Nino, Profesional, SolicitudAtencion
from app.services import adjuntos as servicio_adjuntos
from app.services import atencion
from app.services.acceso import (
    autorizacion_vigente, autorizaciones_vigentes_nino, es_profesional, nino_accesible, nino_del_cuidador,
)
from app.services.auditoria import registrar_actividad, registrar_seguridad
from app.services.notificaciones import marcar_leidas_de, notificar
from app.services.resumen_nino import resumir

ROLES_CUIDADOR = ('cuidador', 'admin')


def _mensajes_de(nino_id, profesional_id):
    return (Mensaje.query.filter_by(nino_id=nino_id, profesional_conversacion_id=profesional_id)
            .order_by(Mensaje.fecha.asc(), Mensaje.id.asc()).all())


def _nuevos_json(nino, profesional_id, desde):
    """Mensajes posteriores a `desde` (id) de una conversación, para mostrarlos sin recargar la página."""
    from app.fechas import fecha_hora
    soy_profesional = es_profesional()
    nuevos = (Mensaje.query.filter(Mensaje.nino_id == nino.id, Mensaje.profesional_conversacion_id == profesional_id,
                                   Mensaje.id > desde)
              .order_by(Mensaje.id.asc()).limit(50).all())
    if nuevos:
        marcar_leidas_de(current_user, 'mensajes', nino.id)
    return jsonify({'mensajes': [{
        'id': m.id,
        'propio': (m.autor_tipo == 'profesional') if soy_profesional else (m.autor_tipo == 'cuidador'),
        'autor': m.nombre_autor(),
        'contenido': m.contenido,
        'fecha': fecha_hora(m.fecha),
        'adjuntos': [{'tipo': a.tipo, 'nombre': a.nombre_original,
                      'tamano': servicio_adjuntos.tamano_legible(a.tamano),
                      'url': url_for('mensajes.adjunto', adjunto_id=a.id)} for a in m.adjuntos],
    } for m in nuevos]})


def _nino_para_profesional(nino_id):
    """Niño/a con quien el profesional tiene relación de atención (autorización vigente o un caso)."""
    nino = db.session.get(Nino, nino_id)
    if nino is None or not nino.activo or not nino.consentimiento_otorgado \
            or not atencion.hay_relacion(nino_id, current_user.id):
        registrar_seguridad('acceso_denegado', descripcion=f'nino_id={nino_id}')
        abort(404)
    return nino


def _guardar(nino, profesional_id, form):
    """Guarda el mensaje (texto y/o adjunto) en la conversación del profesional indicado y avisa solo a la otra parte.
    Devuelve False si no se pudo guardar (el motivo ya se mostró al usuario)."""
    archivo = request.files.get('adjunto')
    tiene_archivo = bool(archivo and archivo.filename)
    texto = (form.contenido.data or '').strip()
    if not texto and not tiene_archivo:
        flash('Escribe un mensaje o adjunta un archivo.', 'danger')
        return False
    mensaje = Mensaje(nino_id=nino.id, profesional_conversacion_id=profesional_id, contenido=texto)
    if tiene_archivo:
        try:
            servicio_adjuntos.guardar(archivo, mensaje)
        except servicio_adjuntos.AdjuntoInvalido as error:
            db.session.rollback()
            flash(str(error), 'danger')
            return False
    if es_profesional():
        mensaje.autor_tipo = 'profesional'
        mensaje.autor_profesional_id = current_user.id
        notificar(nino.cuidador_id, 'cuidador', 'nuevo_mensaje', 'Nuevo mensaje de un profesional',
                  f'{current_user.nombre_con_titulo} escribió sobre {nino.nombre}.', 'mensajes', nino.id)
    else:
        mensaje.autor_tipo = 'cuidador'
        mensaje.autor_cuidador_id = current_user.id
        notificar(profesional_id, 'profesional', 'nuevo_mensaje', 'Nuevo mensaje del cuidador',
                  f'Hay un mensaje nuevo sobre {nino.nombre}.', 'mensajes', nino.id)
    db.session.add(mensaje)
    db.session.commit()
    registrar_actividad('enviar_mensaje', 'nino', nino.id,
                        detalles={'mensaje_id': mensaje.id, 'profesional_id': profesional_id,
                                  'adjuntos': [a.tipo for a in mensaje.adjuntos]})
    return True


# ---------------------------------------------------------------- Conversaciones

@mensajes_bp.route('/nino/<int:nino_id>', methods=['GET', 'POST'])
@login_required
@limiter.limit('30 per minute', methods=['POST'])
def conversacion(nino_id):
    """Profesional: su conversación con el cuidador. Cuidador: bandeja con una conversación por profesional."""
    if not es_profesional():
        nino = nino_accesible(nino_id)
        if request.method == 'POST':
            abort(400)  # el cuidador siempre escribe dentro de la conversación de un profesional
        return _bandeja(nino)

    nino = _nino_para_profesional(nino_id)
    form = MensajeForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            _guardar(nino, current_user.id, form)
        else:
            flash(primer_error(form), 'danger')
        return redirect(url_for('mensajes.conversacion', nino_id=nino.id))
    marcar_leidas_de(current_user, 'mensajes', nino.id)
    caso = atencion.caso_abierto(nino.id, current_user.id)
    return render_template(
        'mensajes/conversacion.html', nino=nino, profesional=current_user, form=form, puede_escribir=True,
        mensajes=_mensajes_de(nino.id, current_user.id), caso=caso,
        expediente=autorizacion_vigente(nino.id, current_user.id) is not None, resumen=resumir(nino),
        llamada=_llamada_activa(nino.id, current_user.id), puede_llamar=_puede_llamar(nino.id, current_user.id),
    )


def _llamada_activa(nino_id, profesional_id):
    from app.services.videollamadas import activa_entre
    return activa_entre(nino_id, profesional_id)


def _puede_llamar(nino_id, profesional_id):
    from app.services.videollamadas import puede_llamar
    return puede_llamar(nino_id, profesional_id)


def _bandeja(nino):
    vigentes = {a.profesional_id for a in autorizaciones_vigentes_nino(nino.id)}
    # También aparecen los profesionales con historial de mensajes (p. ej. de un caso ya cerrado).
    con_mensajes = {pid for (pid,) in db.session.query(Mensaje.profesional_conversacion_id)
                    .filter(Mensaje.nino_id == nino.id, Mensaje.profesional_conversacion_id.isnot(None)).distinct()}
    conversaciones = []
    for profesional in Profesional.query.filter(Profesional.id.in_(vigentes | con_mensajes)).all():
        mensajes = _mensajes_de(nino.id, profesional.id)
        conversaciones.append({'profesional': profesional,
                               'puede_escribir': atencion.hay_relacion(nino.id, profesional.id),
                               'ultimo': mensajes[-1] if mensajes else None})
    conversaciones.sort(key=lambda c: (not c['puede_escribir'], -(c['ultimo'].id if c['ultimo'] else 0)))
    anteriores = (Mensaje.query.filter_by(nino_id=nino.id, profesional_conversacion_id=None)
                  .order_by(Mensaje.fecha.asc()).all())
    return render_template('mensajes/bandeja.html', nino=nino, conversaciones=conversaciones, anteriores=anteriores,
                           solicitud=atencion.solicitud_abierta(nino.id), form=SolicitudAtencionForm(),
                           resumen=resumir(nino))


@mensajes_bp.route('/nino/<int:nino_id>/profesional/<int:profesional_id>', methods=['GET', 'POST'])
@login_required
@limiter.limit('30 per minute', methods=['POST'])
def hilo(nino_id, profesional_id):
    """Conversación del cuidador con un profesional concreto."""
    if es_profesional():
        abort(404)
    nino = nino_accesible(nino_id)  # 404 si el niño/a no es del cuidador
    alguna_vez = (Autorizacion.query.filter_by(nino_id=nino.id, profesional_id=profesional_id).first()
                  or SolicitudAtencion.query.filter_by(nino_id=nino.id, profesional_id=profesional_id).first())
    if not alguna_vez:
        abort(404)
    profesional = db.session.get(Profesional, profesional_id) or abort(404)
    puede_escribir = atencion.hay_relacion(nino.id, profesional_id)

    form = MensajeForm()
    if request.method == 'POST':
        if not puede_escribir:
            abort(403)  # autorización revocada o vencida y sin caso: solo lectura
        if form.validate_on_submit():
            _guardar(nino, profesional_id, form)
        else:
            flash(primer_error(form), 'danger')
        return redirect(url_for('mensajes.hilo', nino_id=nino.id, profesional_id=profesional_id))
    marcar_leidas_de(current_user, 'mensajes', nino.id)
    caso = atencion.caso_abierto(nino.id, profesional_id)
    return render_template('mensajes/conversacion.html', nino=nino, profesional=profesional, form=form,
                           mensajes=_mensajes_de(nino.id, profesional_id), puede_escribir=puede_escribir,
                           caso=caso, llamada=_llamada_activa(nino.id, profesional_id))


@mensajes_bp.route('/nino/<int:nino_id>/nuevos')
@login_required
def nuevos_profesional(nino_id):
    """Mensajes nuevos de la conversación del profesional (static/js/chat_tiempo_real.js)."""
    if not es_profesional():
        abort(404)
    nino = _nino_para_profesional(nino_id)
    return _nuevos_json(nino, current_user.id, request.args.get('desde', 0, type=int))


@mensajes_bp.route('/nino/<int:nino_id>/profesional/<int:profesional_id>/nuevos')
@login_required
def nuevos_cuidador(nino_id, profesional_id):
    if es_profesional():
        abort(404)
    nino = nino_accesible(nino_id)
    return _nuevos_json(nino, profesional_id, request.args.get('desde', 0, type=int))


@mensajes_bp.route('/adjunto/<int:adjunto_id>')
@login_required
def adjunto(adjunto_id):
    """Entrega un adjunto solo a quien puede ver esa conversación (el cuidador del niño/a o el profesional de la
    conversación). Nunca se sirve desde /static."""
    item = db.session.get(AdjuntoMensaje, adjunto_id)
    if item is None:
        abort(404)
    mensaje = item.mensaje
    if es_profesional():
        permitido = (mensaje.profesional_conversacion_id == current_user.id
                     and atencion.hay_relacion(mensaje.nino_id, current_user.id))
    else:
        permitido = mensaje.nino.cuidador_id == current_user.id
    if not permitido:
        registrar_seguridad('acceso_denegado', descripcion=f'adjunto_id={adjunto_id}')
        abort(404)
    registrar_actividad('ver_adjunto', 'nino', mensaje.nino_id, detalles={'adjunto_id': item.id})
    respuesta = send_file(servicio_adjuntos.ruta(item), mimetype=item.mime, download_name=item.nombre_original,
                          as_attachment=item.tipo == 'documento', conditional=True, max_age=0)
    respuesta.headers['Cache-Control'] = 'private, no-store'
    respuesta.headers['X-Content-Type-Options'] = 'nosniff'
    return respuesta


# ---------------------------------------------------------------- Atención: lado del cuidador

def _solicitud_del_cuidador(solicitud_id):
    solicitud = db.session.get(SolicitudAtencion, solicitud_id)
    if solicitud is None or solicitud.cuidador_id != current_user.id:
        abort(404)
    return solicitud


@mensajes_bp.route('/nino/<int:nino_id>/solicitar', methods=['POST'])
@login_required
@rol_requerido(*ROLES_CUIDADOR)
@limiter.limit('5 per minute;20 per day')
def solicitar(nino_id):
    nino = nino_del_cuidador(nino_id, solo_activos=True)
    if not nino.consentimiento_otorgado:
        return redirect(url_for('pacientes.consentimiento', nino_id=nino.id))
    form = SolicitudAtencionForm()
    if not form.validate_on_submit():
        flash(primer_error(form), 'danger')
        return redirect(url_for('mensajes.conversacion', nino_id=nino.id))
    solicitud, _ = atencion.crear_solicitud(nino, current_user, form.motivo.data)
    return redirect(url_for('mensajes.solicitud', solicitud_id=solicitud.id))


@mensajes_bp.route('/solicitud/<int:solicitud_id>')
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def solicitud(solicitud_id):
    item = _solicitud_del_cuidador(solicitud_id)
    if item.estado == 'asignada' and item.acceso is not None:
        return redirect(url_for('mensajes.hilo', nino_id=item.nino_id, profesional_id=item.profesional_id))
    return render_template('mensajes/solicitud.html', solicitud=item, nino=item.nino, resumen=resumir(item.nino))


@mensajes_bp.route('/solicitud/<int:solicitud_id>/estado')
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def solicitud_estado(solicitud_id):
    """Consulta periódica de la pantalla "Conectando..." (static/js/atencion.js)."""
    return jsonify({'estado': _solicitud_del_cuidador(solicitud_id).estado})


@mensajes_bp.route('/solicitud/<int:solicitud_id>/acceso', methods=['POST'])
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def acceso(solicitud_id):
    item = _solicitud_del_cuidador(solicitud_id)
    if item.estado != 'asignada':
        abort(400)
    otorga = request.form.get('respuesta') == 'si'
    atencion.responder_acceso(item, otorga)
    profesional = item.profesional.nombre_con_titulo
    flash(f'Autorizaste a {profesional} a ver la información de {item.nino.nombre}.' if otorga else
          f'{profesional} te atenderá solo con el resumen del semáforo y lo que le escribas. '
          'Puedes autorizarlo después en "Profesionales autorizados".', 'success' if otorga else 'info')
    return redirect(url_for('mensajes.hilo', nino_id=item.nino_id, profesional_id=item.profesional_id))


@mensajes_bp.route('/solicitud/<int:solicitud_id>/cancelar', methods=['POST'])
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def cancelar(solicitud_id):
    item = _solicitud_del_cuidador(solicitud_id)
    if item.estado == 'pendiente':
        atencion.cancelar(item)
        flash('Cancelaste la solicitud.', 'info')
    return redirect(url_for('mensajes.conversacion', nino_id=item.nino_id))


# ---------------------------------------------------------------- Atención: lado del profesional

@mensajes_bp.route('/solicitudes')
@login_required
@rol_requerido('profesional')
def solicitudes():
    mis_casos = (SolicitudAtencion.query.filter_by(profesional_id=current_user.id, estado='asignada')
                 .order_by(SolicitudAtencion.fecha_asignacion.desc()).all())
    pendientes = atencion.pendientes()
    return render_template(
        'mensajes/solicitudes.html', pendientes=pendientes, mis_casos=mis_casos,
        resumenes={s.nino_id: resumir(s.nino) for s in pendientes + mis_casos},
        cupo=atencion.cupo(), puede_recibir=atencion.puede_recibir(current_user),
    )


@mensajes_bp.route('/solicitud/<int:solicitud_id>/atender', methods=['POST'])
@login_required
@rol_requerido('profesional')
def atender(solicitud_id):
    item = atencion.aceptar(solicitud_id, current_user._get_current_object())
    if item is None:
        flash('No fue posible asignarte esta solicitud: otro profesional ya la tomó o alcanzaste tu cupo de casos.',
              'warning')
        return redirect(url_for('mensajes.solicitudes'))
    flash(f'Atiendes ahora a {item.nino.nombre}. ' + (
        'El cuidador autorizó de antemano tu acceso al expediente completo.' if item.acceso == 'otorgado'
        else 'El cuidador decidirá si te autoriza a ver su expediente completo.'), 'success')
    return redirect(url_for('mensajes.conversacion', nino_id=item.nino_id))


@mensajes_bp.route('/solicitud/<int:solicitud_id>/cerrar', methods=['POST'])
@login_required
@rol_requerido('profesional')
def cerrar(solicitud_id):
    item = db.session.get(SolicitudAtencion, solicitud_id)
    if item is None or item.profesional_id != current_user.id or item.estado != 'asignada':
        abort(404)
    atencion.cerrar(item)
    from app.services.videollamadas import terminar_sin_permiso
    terminar_sin_permiso(item.nino_id, current_user.id)  # sin autorización, la llamada termina con el caso
    flash(f'Cerraste el caso de {item.nino.nombre}. La conversación queda disponible para futuros mensajes.', 'success')
    return redirect(url_for('mensajes.solicitudes'))


@mensajes_bp.route('/disponibilidad', methods=['POST'])
@login_required
@rol_requerido('profesional')
def disponibilidad():
    current_user.disponible = request.form.get('disponible') == 'si'
    db.session.commit()
    registrar_actividad('cambiar_disponibilidad', 'profesional', current_user.id,
                        detalles={'disponible': current_user.disponible})
    flash('Ahora recibes nuevas solicitudes.' if current_user.disponible
          else 'Dejaste de recibir nuevas solicitudes. Tus casos abiertos siguen activos.', 'info')
    return redirect(url_for('mensajes.solicitudes'))
