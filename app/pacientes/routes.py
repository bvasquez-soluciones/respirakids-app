from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.pacientes import pacientes_bp
from app.decorators import rol_requerido
from app.models import Nino, Autorizacion, Profesional, PatologiaBase
from app import db


@pacientes_bp.route('/')
@login_required
@rol_requerido('cuidador', 'admin')
def listar():
    ninos = Nino.query.filter_by(cuidador_id=current_user.id).all()
    return render_template('pacientes/listar.html', ninos=ninos)


@pacientes_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
@rol_requerido('cuidador', 'admin')
def nuevo():
    if request.method == 'POST':
        nombre_ficticio = request.form.get('nombre_ficticio')
        fecha_nacimiento = request.form.get('fecha_nacimiento')
        sexo = request.form.get('sexo')

        nuevo_nino = Nino(
            nombre_ficticio=nombre_ficticio,
            fecha_nacimiento=datetime.strptime(fecha_nacimiento, '%Y-%m-%d').date(),
            sexo=sexo,
            cuidador_id=current_user.id
        )

        db.session.add(nuevo_nino)
        db.session.commit()

        flash('Paciente registrado correctamente.', 'success')
        return redirect(url_for('pacientes.listar'))

    return render_template('pacientes/nuevo.html')


@pacientes_bp.route('/<int:nino_id>/editar', methods=['GET', 'POST'])
@login_required
@rol_requerido('cuidador', 'admin')
def editar(nino_id):
    nino = Nino.query.get_or_404(nino_id)

    if nino.cuidador_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        nino.nombre_ficticio = request.form.get('nombre_ficticio')
        nino.fecha_nacimiento = datetime.strptime(request.form.get('fecha_nacimiento'), '%Y-%m-%d').date()
        nino.sexo = request.form.get('sexo')

        db.session.commit()
        flash('Datos del paciente actualizados.', 'success')
        return redirect(url_for('pacientes.listar'))

    return render_template('pacientes/editar.html', nino=nino)


@pacientes_bp.route('/<int:nino_id>/eliminar', methods=['POST'])
@login_required
@rol_requerido('cuidador', 'admin')
def eliminar(nino_id):
    nino = Nino.query.get_or_404(nino_id)

    if nino.cuidador_id != current_user.id:
        abort(403)

    nino.estado = 'inactivo'
    db.session.commit()

    flash('Paciente eliminado (desactivado).', 'info')
    return redirect(url_for('pacientes.listar'))


@pacientes_bp.route('/<int:nino_id>/autorizaciones', methods=['GET', 'POST'])
@login_required
@rol_requerido('cuidador', 'admin')
def autorizaciones(nino_id):
    nino = Nino.query.get_or_404(nino_id)
    if nino.cuidador_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        correo_profesional = request.form.get('correo_profesional')
        profesional = Profesional.query.filter_by(correo=correo_profesional).first()

        if not profesional:
            flash('No se encontró ningún profesional con ese correo.', 'danger')
        else:
            ya_autorizado = Autorizacion.query.filter_by(
                nino_id=nino.id, profesional_id=profesional.id, activa=True
            ).first()
            if ya_autorizado:
                flash('Ese profesional ya tiene autorización activa.', 'warning')
            else:
                nueva_autorizacion = Autorizacion(nino_id=nino.id, profesional_id=profesional.id)
                db.session.add(nueva_autorizacion)
                db.session.commit()
                flash(f'Autorización otorgada a {profesional.nombre}.', 'success')

        return redirect(url_for('pacientes.autorizaciones', nino_id=nino.id))

    lista_autorizaciones = Autorizacion.query.filter_by(nino_id=nino.id, activa=True).all()
    return render_template('pacientes/autorizaciones.html', nino=nino, autorizaciones=lista_autorizaciones)


@pacientes_bp.route('/<int:nino_id>/autorizaciones/<int:autorizacion_id>/revocar', methods=['POST'])
@login_required
@rol_requerido('cuidador', 'admin')
def revocar_autorizacion(nino_id, autorizacion_id):
    nino = Nino.query.get_or_404(nino_id)
    if nino.cuidador_id != current_user.id:
        abort(403)

    autorizacion = Autorizacion.query.get_or_404(autorizacion_id)
    autorizacion.activa = False
    db.session.commit()

    flash('Autorización revocada.', 'info')
    return redirect(url_for('pacientes.autorizaciones', nino_id=nino.id))


@pacientes_bp.route('/<int:nino_id>/patologias', methods=['GET', 'POST'])
@login_required
@rol_requerido('cuidador', 'admin')
def patologias(nino_id):
    nino = Nino.query.get_or_404(nino_id)
    if nino.cuidador_id != current_user.id:
        abort(403)

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        fecha_diagnostico = request.form.get('fecha_diagnostico')

        if not nombre:
            flash('Debes indicar el nombre de la condición o patología.', 'danger')
            return redirect(url_for('pacientes.patologias', nino_id=nino.id))

        nueva_patologia = PatologiaBase(
            nino_id=nino.id,
            nombre=nombre,
            descripcion=descripcion or None,
            fecha_diagnostico=datetime.strptime(fecha_diagnostico, '%Y-%m-%d').date() if fecha_diagnostico else None
        )
        db.session.add(nueva_patologia)
        db.session.commit()

        flash('Condición de base registrada.', 'success')
        return redirect(url_for('pacientes.patologias', nino_id=nino.id))

    lista_patologias = PatologiaBase.query.filter_by(nino_id=nino.id, activa=True).order_by(PatologiaBase.fecha_registro.desc()).all()
    return render_template('pacientes/patologias.html', nino=nino, patologias=lista_patologias)


@pacientes_bp.route('/<int:nino_id>/patologias/<int:patologia_id>/eliminar', methods=['POST'])
@login_required
@rol_requerido('cuidador', 'admin')
def eliminar_patologia(nino_id, patologia_id):
    nino = Nino.query.get_or_404(nino_id)
    if nino.cuidador_id != current_user.id:
        abort(403)

    patologia = PatologiaBase.query.get_or_404(patologia_id)
    patologia.activa = False
    db.session.commit()

    flash('Condición de base eliminada.', 'info')
    return redirect(url_for('pacientes.patologias', nino_id=nino.id))