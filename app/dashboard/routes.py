from flask import render_template, abort, request, redirect, url_for, Response, flash
from flask_login import login_required, current_user
from app.dashboard import dashboard_bp
from app.decorators import rol_requerido
from collections import Counter
import json
import io


@dashboard_bp.context_processor
def inject_alertas():
    if current_user.is_authenticated and current_user.rol == 'profesional':
        from app.models import Autorizacion
        autorizaciones = Autorizacion.query.filter_by(profesional_id=current_user.id, activa=True).all()
        count = 0
        for a in autorizaciones:
            ultima = sorted(a.nino.evaluaciones, key=lambda e: e.fecha)[-1] if a.nino.evaluaciones else None
            if ultima and ultima.nivel_riesgo == 'rojo':
                count += 1
        return {'alertas_rojas_count': count}
    return {'alertas_rojas_count': 0}


@dashboard_bp.route('/cuidador')
@login_required
@rol_requerido('cuidador', 'admin')
def cuidador():
    from app.models import Nino, RegistroSintomas, Evaluacion

    ninos = Nino.query.filter_by(cuidador_id=current_user.id, estado='activo').all()

    ultima_evaluacion = (
        Evaluacion.query
        .join(Nino, Evaluacion.nino_id == Nino.id)
        .filter(Nino.cuidador_id == current_user.id)
        .order_by(Evaluacion.fecha.desc())
        .first()
    )

    ultimos_sintomas = (
        RegistroSintomas.query
        .join(Nino, RegistroSintomas.nino_id == Nino.id)
        .filter(Nino.cuidador_id == current_user.id)
        .order_by(RegistroSintomas.fecha.desc())
        .limit(5)
        .all()
    )

    return render_template(
        'dashboard/cuidador.html',
        usuario=current_user,
        ninos=ninos,
        ultima_evaluacion=ultima_evaluacion,
        ultimos_sintomas=ultimos_sintomas
    )


@dashboard_bp.route('/profesional')
@login_required
@rol_requerido('profesional')
def profesional():
    from app.models import Autorizacion, Nino, RegistroSintomas
    from datetime import datetime, timedelta

    autorizaciones = Autorizacion.query.filter_by(profesional_id=current_user.id, activa=True).all()

    paciente_id = request.args.get('paciente', type=int)
    rango = request.args.get('rango', '7')  # '7', '30', '90' o 'todo'

    nino_seleccionado = None
    registros = []
    chart_labels = '[]'
    chart_data = '[]'
    nivel_actual = 'neutro'

    if paciente_id:
        autorizado = any(a.nino_id == paciente_id for a in autorizaciones)
        if autorizado:
            nino_seleccionado = Nino.query.get_or_404(paciente_id)

            # Historial completo (siempre se muestra entero, sin filtrar por rango)
            registros = RegistroSintomas.query.filter_by(nino_id=paciente_id).order_by(RegistroSintomas.fecha.desc()).all()
            if registros and registros[0].evaluacion:
                nivel_actual = registros[0].evaluacion.nivel_riesgo

            # Datos del gráfico, sí filtrados por el rango elegido
            grafico_query = RegistroSintomas.query.filter_by(nino_id=paciente_id)
            if rango != 'todo':
                dias = int(rango)
                desde = datetime.utcnow() - timedelta(days=dias)
                grafico_query = grafico_query.filter(RegistroSintomas.fecha >= desde)
            registros_grafico = grafico_query.order_by(RegistroSintomas.fecha.asc()).all()

            chart_labels = json.dumps([r.fecha.strftime('%d/%m') for r in registros_grafico])
            chart_data = json.dumps([r.severidad if r.severidad is not None else 0 for r in registros_grafico])

    return render_template(
        'dashboard/profesional.html',
        usuario=current_user,
        autorizaciones=autorizaciones,
        nino_seleccionado=nino_seleccionado,
        registros=registros,
        chart_labels=chart_labels,
        chart_data=chart_data,
        nivel_actual=nivel_actual,
        rango_actual=rango
    )


@dashboard_bp.route('/admin')
@login_required
@rol_requerido('admin')
def admin():
    return render_template('dashboard/admin.html', usuario=current_user)


@dashboard_bp.route('/paciente/<int:nino_id>')
@login_required
@rol_requerido('profesional')
def ver_paciente(nino_id):
    return redirect(url_for('dashboard.profesional', paciente=nino_id))


@dashboard_bp.route('/perfil')
@login_required
@rol_requerido('cuidador', 'admin')
def perfil():
    return render_template('dashboard/perfil.html', usuario=current_user)


@dashboard_bp.route('/reportes')
@login_required
@rol_requerido('profesional')
def reportes():
    from app.models import Autorizacion

    autorizaciones = Autorizacion.query.filter_by(profesional_id=current_user.id, activa=True).all()

    conteo_riesgo = {'verde': 0, 'amarillo': 0, 'rojo': 0, 'neutro': 0}
    conteo_sintomas = Counter()
    filas_tabla = []

    campos_sintomas = {
        'tos': 'Tos', 'dificultad_respiratoria': 'Dificultad respiratoria',
        'respiracion_rapida': 'Respiración rápida', 'congestion_nasal': 'Congestión nasal',
        'secrecion_nasal': 'Secreción nasal', 'dolor_garganta': 'Dolor de garganta',
        'decaimiento': 'Decaimiento', 'perdida_apetito': 'Pérdida de apetito',
        'vomito': 'Vómito', 'diarrea': 'Diarrea', 'estornudos': 'Estornudos',
        'irritabilidad': 'Irritabilidad'
    }

    for a in autorizaciones:
        nino = a.nino
        ultima_eval = sorted(nino.evaluaciones, key=lambda e: e.fecha)[-1] if nino.evaluaciones else None
        nivel = ultima_eval.nivel_riesgo if ultima_eval else 'neutro'
        conteo_riesgo[nivel] += 1

        for r in nino.registros_sintomas:
            for campo, etiqueta in campos_sintomas.items():
                if getattr(r, campo, False):
                    conteo_sintomas[etiqueta] += 1

        filas_tabla.append({
            'nombre': nino.nombre_ficticio,
            'edad': nino.edad_texto(),
            'nivel': nivel,
            'fecha_ultima': ultima_eval.fecha.strftime('%d/%m/%Y %H:%M') if ultima_eval else 'Sin registros',
            'total_registros': len(nino.registros_sintomas)
        })

    top_sintomas = conteo_sintomas.most_common(8)

    riesgo_labels = json.dumps(['Estable (verde)', 'En vigilancia (amarillo)', 'Requiere atención (rojo)', 'Sin registros'])
    riesgo_data = json.dumps([conteo_riesgo['verde'], conteo_riesgo['amarillo'], conteo_riesgo['rojo'], conteo_riesgo['neutro']])
    sintomas_labels = json.dumps([s[0] for s in top_sintomas])
    sintomas_data = json.dumps([s[1] for s in top_sintomas])

    return render_template(
        'dashboard/reportes.html',
        usuario=current_user,
        riesgo_labels=riesgo_labels,
        riesgo_data=riesgo_data,
        sintomas_labels=sintomas_labels,
        sintomas_data=sintomas_data,
        filas_tabla=filas_tabla,
        total_pacientes=len(autorizaciones)
    )


@dashboard_bp.route('/reportes/exportar-pdf')
@login_required
@rol_requerido('profesional')
def exportar_pdf():
    from app.models import Autorizacion
    from flask import Response
    from xhtml2pdf import pisa
    from datetime import datetime
    import io

    autorizaciones = Autorizacion.query.filter_by(profesional_id=current_user.id, activa=True).all()

    filas = []
    for a in autorizaciones:
        nino = a.nino
        ultima_eval = sorted(nino.evaluaciones, key=lambda e: e.fecha)[-1] if nino.evaluaciones else None
        filas.append({
            'nombre': nino.nombre_ficticio,
            'edad': nino.edad_texto(),
            'nivel': ultima_eval.nivel_riesgo if ultima_eval else 'sin registros',
            'fecha': ultima_eval.fecha.strftime('%d/%m/%Y %H:%M') if ultima_eval else '—',
            'total': len(nino.registros_sintomas)
        })

    html_renderizado = render_template(
        'dashboard/reporte_pdf.html',
        usuario=current_user,
        filas=filas,
        fecha_generacion=datetime.utcnow().strftime('%d/%m/%Y %H:%M')
    )

    buffer_pdf = io.BytesIO()
    pisa.CreatePDF(html_renderizado, dest=buffer_pdf)
    buffer_pdf.seek(0)

    return Response(
        buffer_pdf.getvalue(),
        mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=reporte_pacientes_respirakids.pdf'}
    )


@dashboard_bp.route('/ajustes', methods=['GET', 'POST'])
@login_required
@rol_requerido('profesional')
def ajustes():
    from app import db
    import os
    from werkzeug.utils import secure_filename

    EXTENSIONES_PERMITIDAS = {'jpg', 'jpeg', 'png', 'webp'}
    TAMANO_MAXIMO_MB = 3

    if request.method == 'POST':
        accion = request.form.get('accion')

        if accion == 'actualizar_perfil':
            nombre = request.form.get('nombre', '').strip()
            especialidad = request.form.get('especialidad', '').strip()
            numero_licencia = request.form.get('numero_licencia', '').strip()

            if not nombre:
                flash('El nombre no puede estar vacío.', 'danger')
                return redirect(url_for('dashboard.ajustes'))

            # --- Manejo de la foto de perfil ---
            archivo = request.files.get('foto')
            if archivo and archivo.filename:
                extension = archivo.filename.rsplit('.', 1)[-1].lower()

                if extension not in EXTENSIONES_PERMITIDAS:
                    flash('Formato de imagen no permitido. Usa JPG, PNG o WEBP.', 'danger')
                    return redirect(url_for('dashboard.ajustes'))

                archivo.seek(0, os.SEEK_END)
                tamano_mb = archivo.tell() / (1024 * 1024)
                archivo.seek(0)
                if tamano_mb > TAMANO_MAXIMO_MB:
                    flash(f'La imagen no puede superar {TAMANO_MAXIMO_MB} MB.', 'danger')
                    return redirect(url_for('dashboard.ajustes'))

                nombre_archivo = secure_filename(f"profesional_{current_user.id}.{extension}")
                carpeta = os.path.join('app', 'static', 'uploads', 'avatars')
                os.makedirs(carpeta, exist_ok=True)
                ruta_completa = os.path.join(carpeta, nombre_archivo)
                archivo.save(ruta_completa)
                current_user.foto = f"uploads/avatars/{nombre_archivo}"

            current_user.nombre = nombre
            current_user.especialidad = especialidad or None
            current_user.numero_licencia = numero_licencia or None
            db.session.commit()
            flash('Perfil actualizado correctamente.', 'success')
            return redirect(url_for('dashboard.ajustes'))

        elif accion == 'cambiar_password':
            actual = request.form.get('password_actual', '')
            nueva = request.form.get('password_nueva', '')
            confirmar = request.form.get('password_confirmar', '')

            if not current_user.check_password(actual):
                flash('La contraseña actual no es correcta.', 'danger')
            elif len(nueva) < 8:
                flash('La nueva contraseña debe tener al menos 8 caracteres.', 'danger')
            elif nueva != confirmar:
                flash('Las contraseñas nuevas no coinciden.', 'danger')
            else:
                current_user.set_password(nueva)
                db.session.commit()
                flash('Contraseña actualizada correctamente.', 'success')
            return redirect(url_for('dashboard.ajustes'))

    return render_template('dashboard/ajustes.html', usuario=current_user)


@dashboard_bp.route('/alertas')
@login_required
@rol_requerido('profesional')
def alertas():
    from app.models import Autorizacion
    autorizaciones = Autorizacion.query.filter_by(profesional_id=current_user.id, activa=True).all()
    pacientes_rojo = []
    for a in autorizaciones:
        ultima = sorted(a.nino.evaluaciones, key=lambda e: e.fecha)[-1] if a.nino.evaluaciones else None
        if ultima and ultima.nivel_riesgo == 'rojo':
            pacientes_rojo.append((a.nino, ultima))
    return render_template('dashboard/alertas.html', usuario=current_user, pacientes_rojo=pacientes_rojo)