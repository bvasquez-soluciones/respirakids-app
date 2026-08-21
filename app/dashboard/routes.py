from flask import render_template, abort
from flask_login import login_required, current_user
from app.dashboard import dashboard_bp
from app.decorators import rol_requerido


@dashboard_bp.route('/cuidador')
@login_required
@rol_requerido('cuidador', 'admin')
def cuidador():
    return render_template('dashboard/cuidador.html', usuario=current_user)


@dashboard_bp.route('/profesional')
@login_required
@rol_requerido('profesional')
def profesional():
    from app.models import Autorizacion
    autorizaciones = Autorizacion.query.filter_by(profesional_id=current_user.id, activa=True).all()
    return render_template('dashboard/profesional.html', usuario=current_user, autorizaciones=autorizaciones)


@dashboard_bp.route('/admin')
@login_required
@rol_requerido('admin')
def admin():
    return render_template('dashboard/admin.html', usuario=current_user)


@dashboard_bp.route('/paciente/<int:nino_id>')
@login_required
@rol_requerido('profesional')
def ver_paciente(nino_id):
    from app.models import Autorizacion, Nino, RegistroSintomas

    autorizado = Autorizacion.query.filter_by(
        nino_id=nino_id, profesional_id=current_user.id, activa=True
    ).first()

    if not autorizado:
        abort(403)

    nino = Nino.query.get_or_404(nino_id)
    registros = RegistroSintomas.query.filter_by(nino_id=nino.id).order_by(RegistroSintomas.fecha.desc()).all()

    return render_template('dashboard/ver_paciente.html', nino=nino, registros=registros)