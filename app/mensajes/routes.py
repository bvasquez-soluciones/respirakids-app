from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.mensajes import mensajes_bp
from app.models import Nino, Mensaje, Autorizacion
from app import db


def obtener_nino_con_permiso(nino_id):
    """
    Verifica que el usuario actual (cuidador dueño o profesional autorizado)
    tenga permiso para ver/participar en la conversación de este niño.
    Devuelve el objeto Nino si tiene permiso, o aborta con 403.
    """
    nino = Nino.query.get_or_404(nino_id)

    if current_user.rol in ('cuidador', 'admin') and hasattr(current_user, 'ninos'):
        if nino.cuidador_id == current_user.id:
            return nino

    if current_user.rol == 'profesional':
        autorizado = Autorizacion.query.filter_by(
            nino_id=nino.id, profesional_id=current_user.id, activa=True
        ).first()
        if autorizado:
            return nino

    abort(403)


@mensajes_bp.route('/nino/<int:nino_id>', methods=['GET', 'POST'])
@login_required
def conversacion(nino_id):
    nino = obtener_nino_con_permiso(nino_id)

    if request.method == 'POST':
        contenido = request.form.get('contenido', '').strip()

        if contenido:
            if current_user.rol == 'profesional':
                nuevo_mensaje = Mensaje(
                    nino_id=nino.id,
                    autor_tipo='profesional',
                    autor_profesional_id=current_user.id,
                    contenido=contenido
                )
            else:
                nuevo_mensaje = Mensaje(
                    nino_id=nino.id,
                    autor_tipo='cuidador',
                    autor_cuidador_id=current_user.id,
                    contenido=contenido
                )

            db.session.add(nuevo_mensaje)
            db.session.commit()

        return redirect(url_for('mensajes.conversacion', nino_id=nino.id))

    mensajes = Mensaje.query.filter_by(nino_id=nino.id).order_by(Mensaje.fecha.asc()).all()
    return render_template('mensajes/conversacion.html', nino=nino, mensajes=mensajes)