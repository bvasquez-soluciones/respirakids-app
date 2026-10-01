from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.decorators import rol_requerido
from app.forms import AutorizacionForm, ConsentimientoNinoForm, NinoForm, PatologiaForm
from app.models import Autorizacion, Evaluacion, Nino, PatologiaBase, Profesional
from app.pacientes import pacientes_bp
from app.services.acceso import nino_del_cuidador
from app.services.auditoria import registrar_actividad
from app.services.consentimiento import registrar_consentimiento_nino
from app.services.resumen_nino import resumir

ROLES_CUIDADOR = ('cuidador', 'admin')


def _aplicar_formulario(nino, form):
    nino.nombre = form.nombre.data
    nino.apellido = form.apellido.data
    nino.fecha_nacimiento = form.fecha_nacimiento.data
    nino.sexo = form.sexo.data
    nino.peso_kg = form.peso_kg.data
    nino.talla_cm = form.talla_cm.data


@pacientes_bp.route('/')
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def listar():
    ninos = (
        Nino.query.filter_by(cuidador_id=current_user.id)
        .order_by(Nino.estado, Nino.nombre)
        .all()
    )
    return render_template('pacientes/listar.html', ninos=ninos)


@pacientes_bp.route('/<int:nino_id>')
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def ficha(nino_id):
    nino = nino_del_cuidador(nino_id)
    evaluaciones = (
        Evaluacion.query.filter_by(nino_id=nino.id)
        .order_by(Evaluacion.fecha.desc(), Evaluacion.id.desc())
        .limit(5)
        .all()
    )
    patologias = PatologiaBase.query.filter_by(nino_id=nino.id, activa=True).order_by(PatologiaBase.nombre).all()
    autorizaciones = Autorizacion.query.filter_by(nino_id=nino.id, activa=True).all()
    registrar_actividad('consultar_ficha', 'nino', nino.id)
    return render_template(
        'pacientes/ficha.html', nino=nino, resumen=resumir(nino), evaluaciones=evaluaciones,
        patologias=patologias, autorizaciones=autorizaciones,
    )


@pacientes_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def nuevo():
    form = NinoForm(es_nuevo=True)
    if request.method == 'POST':
        if not form.validate_on_submit():
            return render_template('pacientes/nuevo.html', form=form), 400

        nino = Nino(cuidador_id=current_user.id, estado='activo')
        _aplicar_formulario(nino, form)
        db.session.add(nino)
        db.session.flush()
        registrar_consentimiento_nino(
            current_user, nino,
            tratamiento=form.consentimiento_tratamiento.data,
            investigacion=form.consentimiento_investigacion.data,
        )
        db.session.commit()
        registrar_actividad('crear', 'nino', nino.id)

        flash('Niño/a registrado/a correctamente.', 'success')
        return redirect(url_for('pacientes.listar'))

    return render_template('pacientes/nuevo.html', form=form)


@pacientes_bp.route('/<int:nino_id>/editar', methods=['GET', 'POST'])
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def editar(nino_id):
    nino = nino_del_cuidador(nino_id)
    form = NinoForm(obj=nino, es_nuevo=False)

    if request.method == 'POST':
        if not form.validate_on_submit():
            return render_template('pacientes/editar.html', nino=nino, form=form), 400

        _aplicar_formulario(nino, form)
        db.session.commit()
        registrar_actividad('editar', 'nino', nino.id)
        flash('Datos actualizados.', 'success')
        return redirect(url_for('pacientes.listar'))

    return render_template('pacientes/editar.html', nino=nino, form=form)


@pacientes_bp.route('/<int:nino_id>/eliminar', methods=['POST'])
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def eliminar(nino_id):
    nino = nino_del_cuidador(nino_id)
    nino.estado = 'inactivo'
    db.session.commit()
    registrar_actividad('desactivar', 'nino', nino.id)
    flash('Registro desactivado. La información se conserva y puedes reactivarlo cuando quieras.', 'info')
    return redirect(url_for('pacientes.listar'))


@pacientes_bp.route('/<int:nino_id>/reactivar', methods=['POST'])
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def reactivar(nino_id):
    nino = nino_del_cuidador(nino_id)
    nino.estado = 'activo'
    db.session.commit()
    registrar_actividad('reactivar', 'nino', nino.id)
    flash('Registro reactivado.', 'success')
    return redirect(url_for('pacientes.listar'))


@pacientes_bp.route('/<int:nino_id>/consentimiento', methods=['GET', 'POST'])
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def consentimiento(nino_id):
    nino = nino_del_cuidador(nino_id)
    form = ConsentimientoNinoForm(data=None if request.method == 'POST' else {
        'consentimiento_tratamiento': nino.consentimiento_otorgado,
        'consentimiento_investigacion': nino.consentimiento_investigacion_otorgado,
    })

    if request.method == 'POST' and form.validate_on_submit():
        tratamiento = form.consentimiento_tratamiento.data
        revoca = nino.consentimiento_otorgado and not tratamiento
        registrar_consentimiento_nino(current_user, nino, tratamiento, form.consentimiento_investigacion.data)
        if revoca:
            # Sin autorización de tratamiento, ningún profesional puede seguir accediendo a la información.
            for autorizacion in Autorizacion.query.filter_by(nino_id=nino.id, activa=True):
                autorizacion.activa = False
        db.session.commit()
        registrar_actividad('actualizar_consentimiento', 'nino', nino.id,
                            detalles={'tratamiento': tratamiento, 'investigacion': form.consentimiento_investigacion.data})
        if revoca:
            flash('Revocaste la autorización. Los profesionales ya no tienen acceso y no se podrán registrar '
                  'nuevos síntomas. Para solicitar la supresión de los datos usa la sección Mis datos.', 'info')
        else:
            flash('Autorizaciones actualizadas.', 'success')
        return redirect(url_for('pacientes.listar'))

    return render_template('pacientes/consentimiento.html', nino=nino, form=form)


@pacientes_bp.route('/<int:nino_id>/autorizaciones', methods=['GET', 'POST'])
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def autorizaciones(nino_id):
    nino = nino_del_cuidador(nino_id, solo_activos=True)
    form = AutorizacionForm()

    if request.method == 'POST':
        if not nino.consentimiento_otorgado:
            flash('Para compartir información con profesionales primero debes autorizar el tratamiento de datos.', 'warning')
            return redirect(url_for('pacientes.consentimiento', nino_id=nino.id))
        if not form.validate_on_submit():
            return _render_autorizaciones(nino, form), 400

        profesional = Profesional.query.filter_by(correo=form.correo_profesional.data).first()
        if not profesional or not profesional.aprobado:
            form.correo_profesional.errors.append('No se encontró un profesional habilitado con ese correo.')
            return _render_autorizaciones(nino, form), 400
        if Autorizacion.query.filter_by(nino_id=nino.id, profesional_id=profesional.id, activa=True).first():
            flash('Ese profesional ya tiene autorización activa.', 'warning')
        else:
            autorizacion = Autorizacion(nino_id=nino.id, profesional_id=profesional.id, activa=True)
            db.session.add(autorizacion)
            db.session.commit()
            registrar_actividad('otorgar_acceso', 'nino', nino.id, detalles={'profesional_id': profesional.id})
            flash(f'Autorización otorgada a {profesional.nombre}.', 'success')

        return redirect(url_for('pacientes.autorizaciones', nino_id=nino.id))

    return _render_autorizaciones(nino, form)


def _render_autorizaciones(nino, form):
    lista = Autorizacion.query.filter_by(nino_id=nino.id, activa=True).all()
    return render_template('pacientes/autorizaciones.html', nino=nino, autorizaciones=lista, form=form)


@pacientes_bp.route('/<int:nino_id>/autorizaciones/<int:autorizacion_id>/revocar', methods=['POST'])
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def revocar_autorizacion(nino_id, autorizacion_id):
    nino = nino_del_cuidador(nino_id)
    autorizacion = Autorizacion.query.filter_by(id=autorizacion_id, nino_id=nino.id).first_or_404()
    autorizacion.activa = False
    db.session.commit()
    registrar_actividad('revocar_acceso', 'nino', nino.id, detalles={'profesional_id': autorizacion.profesional_id})
    flash('Autorización revocada.', 'info')
    return redirect(url_for('pacientes.autorizaciones', nino_id=nino.id))


@pacientes_bp.route('/<int:nino_id>/patologias', methods=['GET', 'POST'])
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def patologias(nino_id):
    nino = nino_del_cuidador(nino_id)
    form = PatologiaForm()

    if request.method == 'POST':
        if not form.validate_on_submit():
            return _render_patologias(nino, form), 400

        patologia = PatologiaBase(
            nino_id=nino.id,
            nombre=form.nombre.data,
            descripcion=form.descripcion.data or None,
            fecha_diagnostico=form.fecha_diagnostico.data,
        )
        db.session.add(patologia)
        db.session.commit()
        registrar_actividad('crear', 'patologia_base', patologia.id, detalles={'nino_id': nino.id})
        flash('Condición de base registrada.', 'success')
        return redirect(url_for('pacientes.patologias', nino_id=nino.id))

    return _render_patologias(nino, form)


def _render_patologias(nino, form):
    lista = (
        PatologiaBase.query.filter_by(nino_id=nino.id, activa=True)
        .order_by(PatologiaBase.fecha_registro.desc())
        .all()
    )
    return render_template('pacientes/patologias.html', nino=nino, patologias=lista, form=form)


@pacientes_bp.route('/<int:nino_id>/patologias/<int:patologia_id>/eliminar', methods=['POST'])
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def eliminar_patologia(nino_id, patologia_id):
    nino = nino_del_cuidador(nino_id)
    patologia = PatologiaBase.query.filter_by(id=patologia_id, nino_id=nino.id).first_or_404()
    patologia.activa = False
    db.session.commit()
    registrar_actividad('desactivar', 'patologia_base', patologia.id, detalles={'nino_id': nino.id})
    flash('Condición de base eliminada.', 'info')
    return redirect(url_for('pacientes.patologias', nino_id=nino.id))
