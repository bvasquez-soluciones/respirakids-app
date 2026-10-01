from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.decorators import rol_requerido
from app.fechas import a_utc, ahora_local
from app.forms import RecetaForm
from app.medicamentos import medicamentos_bp
from app.models import Receta, TomaMedicamento
from app.services.acceso import es_profesional, nino_accesible, nino_del_cuidador, nino_del_profesional
from app.services.auditoria import registrar_actividad
from app.services.medicacion import (
    crear_receta, cumplimiento, marcar_toma, recetas_del_nino, suspender_receta, tomas_pendientes,
)


@medicamentos_bp.route('/nino/<int:nino_id>')
@login_required
def plan(nino_id):
    """Indicaciones de medicamentos del niño/a: para el cuidador y para profesionales autorizados."""
    nino = nino_accesible(nino_id)
    recetas = recetas_del_nino(nino)
    registrar_actividad('consultar_medicamentos', 'nino', nino.id)
    return render_template(
        'medicamentos/plan.html', nino=nino, recetas=recetas, tomas=tomas_pendientes(nino),
        cumplimiento=cumplimiento, es_profesional=es_profesional(),
    )


@medicamentos_bp.route('/nino/<int:nino_id>/nueva', methods=['GET', 'POST'])
@login_required
@rol_requerido('profesional')
def nueva(nino_id):
    nino = nino_del_profesional(nino_id)
    form = RecetaForm()
    if request.method == 'GET':
        form.fecha_inicio.data = ahora_local().replace(second=0, microsecond=0)

    if request.method == 'POST':
        if not form.validate_on_submit():
            return render_template('medicamentos/nueva.html', nino=nino, form=form), 400
        receta = crear_receta(
            nino, current_user, motivo=form.motivo.data, indicaciones=form.indicaciones_generales.data or None,
            fecha_inicio_utc=a_utc(form.fecha_inicio.data),
            medicamentos=[entrada.form.datos() for entrada in form.medicamentos],
        )
        registrar_actividad('crear_receta', 'nino', nino.id, detalles={'receta_id': receta.id})
        flash('Indicación registrada. El cuidador fue notificado.', 'success')
        return redirect(url_for('medicamentos.plan', nino_id=nino.id))

    return render_template('medicamentos/nueva.html', nino=nino, form=form)


@medicamentos_bp.route('/receta/<int:receta_id>/suspender', methods=['POST'])
@login_required
@rol_requerido('profesional')
def suspender(receta_id):
    receta = db.session.get(Receta, receta_id) or abort(404)
    nino = nino_del_profesional(receta.nino_id)
    if receta.profesional_id != current_user.id:
        abort(403)  # solo quien la registró puede suspenderla
    if receta.activa:
        suspender_receta(receta, current_user)
        registrar_actividad('suspender_receta', 'nino', nino.id, detalles={'receta_id': receta.id})
        flash('Indicación suspendida. El cuidador fue notificado.', 'info')
    return redirect(url_for('medicamentos.plan', nino_id=nino.id))


@medicamentos_bp.route('/toma/<int:toma_id>/marcar', methods=['POST'])
@login_required
@rol_requerido('cuidador', 'admin')
def marcar(toma_id):
    toma = db.session.get(TomaMedicamento, toma_id) or abort(404)
    receta = toma.medicamento.receta
    nino = nino_del_cuidador(receta.nino_id)
    if not receta.activa or not toma.medicamento.activo:
        abort(404)
    administrada = request.form.get('administrada') == '1'
    marcar_toma(toma, current_user, administrada)
    registrar_actividad('marcar_toma' if administrada else 'desmarcar_toma', 'nino', nino.id,
                        detalles={'toma_id': toma.id})
    flash('Toma registrada.' if administrada else 'Se quitó la marca de la toma.', 'success')
    return redirect(url_for('medicamentos.plan', nino_id=nino.id))
