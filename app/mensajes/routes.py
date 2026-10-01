from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db, limiter
from app.forms import MensajeForm, primer_error
from app.mensajes import mensajes_bp
from app.models import Mensaje
from app.services.acceso import autorizaciones_vigentes_nino, es_profesional, nino_accesible
from app.services.auditoria import registrar_actividad
from app.services.notificaciones import notificar


@mensajes_bp.route('/nino/<int:nino_id>', methods=['GET', 'POST'])
@login_required
@limiter.limit('30 per minute', methods=['POST'])
def conversacion(nino_id):
    nino = nino_accesible(nino_id)
    form = MensajeForm()

    if request.method == 'POST':
        if not form.validate_on_submit():
            flash(primer_error(form), 'danger')
            return redirect(url_for('mensajes.conversacion', nino_id=nino.id))

        mensaje = Mensaje(nino_id=nino.id, contenido=form.contenido.data.strip())
        if es_profesional():
            mensaje.autor_tipo = 'profesional'
            mensaje.autor_profesional_id = current_user.id
            mensaje.profesional_conversacion_id = current_user.id
        else:
            mensaje.autor_tipo = 'cuidador'
            mensaje.autor_cuidador_id = current_user.id
        db.session.add(mensaje)
        _notificar_mensaje(nino)
        db.session.commit()
        registrar_actividad('enviar_mensaje', 'nino', nino.id, detalles={'mensaje_id': mensaje.id})
        return redirect(url_for('mensajes.conversacion', nino_id=nino.id))

    mensajes = Mensaje.query.filter_by(nino_id=nino.id).order_by(Mensaje.fecha.asc()).all()
    return render_template('mensajes/conversacion.html', nino=nino, mensajes=mensajes)


def _notificar_mensaje(nino):
    """Avisa a la otra parte de la conversación: al cuidador o a los profesionales autorizados."""
    if es_profesional():
        notificar(nino.cuidador_id, 'cuidador', 'nuevo_mensaje', 'Nuevo mensaje de un profesional',
                  f'{current_user.nombre_completo} escribió sobre {nino.nombre}.', 'mensajes', nino.id)
    else:
        for autorizacion in autorizaciones_vigentes_nino(nino.id):
            notificar(autorizacion.profesional_id, 'profesional', 'nuevo_mensaje', 'Nuevo mensaje del cuidador',
                      f'Hay un mensaje nuevo sobre {nino.nombre}.', 'mensajes', nino.id)
