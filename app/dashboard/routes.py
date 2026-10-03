import io
import os
from collections import Counter
from datetime import timedelta

from flask import Response, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user
from PIL import Image, UnidentifiedImageError

from app import db
from app.clinica.reglas_v1 import REGLAS_POR_ID
from app.dashboard import dashboard_bp
from app.decorators import rol_requerido
from app.fechas import fecha_hora
from app.forms import CambioPasswordForm, PerfilCuidadorForm, PerfilProfesionalForm
from app.ml.prediccion import concordancia_con_reglas, metadatos_modelo
from app.models import Evaluacion, Nino, RegistroSintomas, ahora_utc
from app.presentacion import (
    SIGNOS_CLINICOS, SINTOMAS_REPORTADOS, datos_complementarios, hallazgos_registrados, nivel_info,
)
from app.services.acceso import autorizaciones_vigentes_profesional, nino_del_profesional
from app.services.alertas import pacientes_en_rojo
from app.services.auditoria import registrar_actividad, registrar_seguridad
from app.services.notificaciones import marcar_todas_leidas, recientes
from app.services.resumen_nino import (
    avisos_de_evaluacion, datos_evolucion, linea_de_tiempo, resumir, resumir_todos, senales_de_evaluacion,
)

FORMATOS_IMAGEN = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}
TAMANO_MAXIMO_FOTO_MB = 3
RANGOS_GRAFICO = {'7': 7, '30': 30, '90': 90, 'todo': None}

CAMPOS_SINTOMAS = {**SIGNOS_CLINICOS, **SINTOMAS_REPORTADOS}  # catálogo único (app/presentacion.py)


# ---------------------------------------------------------------- Cuidador

@dashboard_bp.route('/cuidador')
@login_required
@rol_requerido('cuidador', 'admin')
def cuidador():
    ninos = Nino.query.filter_by(cuidador_id=current_user.id, estado='activo').all()
    return render_template('dashboard/cuidador.html', usuario=current_user, resumenes=resumir_todos(ninos))


def _procesar_cambio_password(form):
    """Valida y aplica el cambio de contraseña. Devuelve True si se cambió."""
    if not form.validate_on_submit():
        return False
    if not current_user.check_password(form.password_actual.data):
        registrar_seguridad('cambio_password_fallido')
        form.password_actual.errors.append('La contraseña actual no es correcta.')
        return False
    current_user.set_password(form.password_nueva.data)
    if hasattr(current_user, 'debe_cambiar_password'):
        current_user.debe_cambiar_password = False
    db.session.commit()
    # La huella de sesión cambió: las sesiones de otros dispositivos se cierran y esta se renueva.
    login_user(current_user._get_current_object())
    registrar_seguridad('cambio_password')
    flash('Contraseña actualizada. Se cerraron las sesiones abiertas en otros dispositivos.', 'success')
    return True


def _formularios_de_cuenta(clase_perfil):
    """Formulario de datos y de contraseña; solo procesa los datos enviados del que corresponda a la acción."""
    accion = request.form.get('accion') if request.method == 'POST' else None
    form_perfil = clase_perfil(formdata=request.form if accion == 'actualizar_perfil' else None, obj=current_user)
    form_password = CambioPasswordForm(formdata=request.form if accion == 'cambiar_password' else None)
    return accion, form_perfil, form_password


@dashboard_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
@rol_requerido('cuidador', 'admin')
def perfil():
    accion, form_perfil, form_password = _formularios_de_cuenta(PerfilCuidadorForm)

    if accion == 'actualizar_perfil' and form_perfil.validate_on_submit():
        current_user.nombre = form_perfil.nombre.data
        current_user.apellido = form_perfil.apellido.data
        current_user.telefono = form_perfil.telefono.data or None
        db.session.commit()
        registrar_actividad('editar', 'cuidador', current_user.id)
        flash('Datos actualizados.', 'success')
        return redirect(url_for('dashboard.perfil'))
    if accion == 'cambiar_password' and _procesar_cambio_password(form_password):
        return redirect(url_for('dashboard.perfil'))

    codigo = 400 if accion else 200
    return render_template('dashboard/perfil.html', usuario=current_user,
                           form_perfil=form_perfil, form_password=form_password), codigo


# ---------------------------------------------------------------- Profesional

@dashboard_bp.route('/semaforo')
@login_required
@rol_requerido('profesional')
def semaforo():
    """Semáforo de la clínica: nivel y señales de la última evaluación de todos los niños/as con autorización
    de tratamiento de datos. El expediente completo solo lo ve el profesional que el cuidador autorice."""
    from app.models import SolicitudAtencion
    ninos = Nino.query.filter_by(estado='activo', consentimiento_otorgado=True).all()
    resumenes = resumir_todos(ninos)
    autorizados = {a.nino_id for a in autorizaciones_vigentes_profesional(current_user.id)}
    en_espera = {s.nino_id for s in SolicitudAtencion.query.filter_by(estado='pendiente').all()}
    registrar_actividad('consultar_semaforo', 'clinica', None, detalles={'ninos': len(resumenes)})
    return render_template('dashboard/semaforo.html', resumenes=resumenes, autorizados=autorizados,
                           en_espera=en_espera, conteo=Counter(r.nivel for r in resumenes))


@dashboard_bp.route('/profesional')
@login_required
@rol_requerido('profesional')
def profesional():
    """Pacientes de la clínica con su semáforo. El expediente completo solo se abre si el cuidador autorizó
    a este profesional; si no, se muestra el resumen del semáforo."""
    from app.models import SolicitudAtencion
    from app.services import atencion
    autorizaciones = autorizaciones_vigentes_profesional(current_user.id)
    autorizados = {a.nino_id for a in autorizaciones}
    pacientes = (Nino.query.filter_by(estado='activo', consentimiento_otorgado=True)
                 .order_by(Nino.nombre, Nino.apellido).all())
    paciente_id = request.args.get('paciente', type=int)
    rango = request.args.get('rango', '30')
    if rango not in RANGOS_GRAFICO:
        rango = '30'

    contexto = {'usuario': current_user, 'autorizaciones': autorizaciones, 'rango_actual': rango,
                'nino_seleccionado': None, 'pacientes': pacientes, 'autorizados': autorizados}
    if paciente_id and paciente_id not in autorizados:
        # Sin autorización del cuidador: solo el resumen del semáforo.
        nino = db.session.get(Nino, paciente_id)
        if nino is None or not nino.activo or not nino.consentimiento_otorgado:
            abort(404)
        registrar_actividad('consultar_semaforo_paciente', 'nino', nino.id)
        contexto.update(
            nino_seleccionado=nino, resumen=resumir(nino), sin_expediente=True,
            puede_conversar=atencion.hay_relacion(nino.id, current_user.id),
            solicitud_en_espera=SolicitudAtencion.query.filter_by(nino_id=nino.id, estado='pendiente').first(),
        )
    elif paciente_id:
        nino = nino_del_profesional(paciente_id)
        registrar_actividad('consultar_paciente', 'nino', nino.id)
        registros = (
            RegistroSintomas.query.filter_by(nino_id=nino.id)
            .order_by(RegistroSintomas.fecha.desc(), RegistroSintomas.id.desc())
            .all()
        )
        dias = RANGOS_GRAFICO[rango]
        en_rango = [r for r in registros if not dias or r.fecha >= ahora_utc() - timedelta(days=dias)]
        resumen = resumir(nino)
        contexto.update(
            nino_seleccionado=nino, registros=registros, resumen=resumen,
            linea=linea_de_tiempo(registros, nino.seguimientos),
            evolucion=datos_evolucion(en_rango),
            avisos=avisos_de_evaluacion(resumen.ultima_evaluacion),
            patologias=[p for p in nino.patologias_base if p.activa],
        )
    return render_template('dashboard/profesional.html', **contexto)


@dashboard_bp.route('/profesional/evaluacion/<int:evaluacion_id>')
@login_required
@rol_requerido('profesional')
def profesional_evaluacion(evaluacion_id):
    """Detalle clínico de una evaluación: reglas aplicadas, criterios citados y datos registrados."""
    evaluacion = db.session.get(Evaluacion, evaluacion_id)
    if evaluacion is None:
        abort(404)
    nino = nino_del_profesional(evaluacion.nino_id)
    registrar_actividad('consultar_evaluacion', 'evaluacion', evaluacion.id)
    registro = evaluacion.registro_sintomas
    return render_template(
        'dashboard/profesional_evaluacion.html', nino=nino, evaluacion=evaluacion, registro=registro,
        senales=senales_de_evaluacion(evaluacion), avisos=avisos_de_evaluacion(evaluacion),
        reglas=REGLAS_POR_ID, hallazgos=hallazgos_registrados(registro),
        complementarios=datos_complementarios(registro),
    )


def _resumen_pacientes(autorizaciones):
    filas = []
    for a in autorizaciones:
        nino = a.nino
        ultima = nino.ultima_evaluacion()
        filas.append({
            'nino': nino,
            'nivel': ultima.nivel_riesgo if ultima else 'neutro',
            'fecha_ultima': ultima.fecha if ultima else None,
            'total_registros': len(nino.registros_sintomas),
        })
    return filas


@dashboard_bp.route('/reportes')
@login_required
@rol_requerido('profesional')
def reportes():
    autorizaciones = autorizaciones_vigentes_profesional(current_user.id)
    filas = _resumen_pacientes(autorizaciones)

    conteo_riesgo = Counter(f['nivel'] for f in filas)
    conteo_sintomas = Counter()
    for a in autorizaciones:
        for r in a.nino.registros_sintomas:
            for campo, etiqueta in CAMPOS_SINTOMAS.items():
                if getattr(r, campo, False):
                    conteo_sintomas[etiqueta] += 1
    top_sintomas = conteo_sintomas.most_common(8)

    filas_tabla = [{
        'nombre': f['nino'].nombre_completo,
        'edad': f['nino'].edad_texto(),
        'nivel': f['nivel'],
        'fecha_ultima': fecha_hora(f['fecha_ultima']) if f['fecha_ultima'] else 'Sin registros',
        'total_registros': f['total_registros'],
    } for f in filas]

    return render_template(
        'dashboard/reportes.html', usuario=current_user,
        niveles=[{'nivel': n, 'nombre': nivel_info(n)['nombre'], 'total': conteo_riesgo[n]}
                 for n in ('rojo', 'amarillo', 'verde', 'neutro')],
        sintomas=[{'etiqueta': etiqueta, 'total': total} for etiqueta, total in top_sintomas],
        filas_tabla=filas_tabla, total_pacientes=len(autorizaciones),
    )


@dashboard_bp.route('/reportes/exportar-pdf')
@login_required
@rol_requerido('profesional')
def exportar_pdf():
    from xhtml2pdf import pisa

    filas = [{
        'nombre': f['nino'].nombre_completo,
        'edad': f['nino'].edad_texto(),
        'nivel': f['nivel'] if f['nivel'] != 'neutro' else 'sin registros',
        'fecha': fecha_hora(f['fecha_ultima']),
        'total': f['total_registros'],
    } for f in _resumen_pacientes(autorizaciones_vigentes_profesional(current_user.id))]

    html = render_template(
        'dashboard/reporte_pdf.html', usuario=current_user, filas=filas,
        fecha_generacion=fecha_hora(ahora_utc()),
    )
    buffer = io.BytesIO()
    resultado = pisa.CreatePDF(html, dest=buffer)
    if resultado.err:
        current_app.logger.error('No se pudo generar el PDF de reporte (errores=%s)', resultado.err)
        flash('No se pudo generar el PDF. Inténtalo de nuevo.', 'danger')
        return redirect(url_for('dashboard.reportes'))

    registrar_actividad('exportar_reporte', 'reporte', None, detalles={'pacientes': len(filas)})
    return Response(
        buffer.getvalue(), mimetype='application/pdf',
        headers={'Content-Disposition': 'attachment; filename=reporte_pacientes_respirakids.pdf'},
    )


@dashboard_bp.route('/alertas')
@login_required
@rol_requerido('profesional')
def alertas():
    return render_template('dashboard/alertas.html', usuario=current_user,
                           pacientes_rojo=pacientes_en_rojo(current_user.id))


def _guardar_foto(archivo):
    """Valida que el archivo sea realmente una imagen y la guarda con un nombre controlado.

    Devuelve la ruta relativa a /static o lanza ValueError con un mensaje para el usuario.
    """
    archivo.seek(0, os.SEEK_END)
    if archivo.tell() > TAMANO_MAXIMO_FOTO_MB * 1024 * 1024:
        raise ValueError(f'La imagen no puede superar {TAMANO_MAXIMO_FOTO_MB} MB.')
    archivo.seek(0)
    try:
        imagen = Image.open(archivo)
        imagen.verify()
    except (UnidentifiedImageError, OSError):
        raise ValueError('El archivo no es una imagen válida.')
    extension = FORMATOS_IMAGEN.get(imagen.format)
    if not extension:
        raise ValueError('Formato de imagen no permitido. Usa JPG, PNG o WEBP.')

    carpeta = os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')
    os.makedirs(carpeta, exist_ok=True)
    for anterior in FORMATOS_IMAGEN.values():  # evita fotos huérfanas con otra extensión
        ruta_anterior = os.path.join(carpeta, f'profesional_{current_user.id}.{anterior}')
        if os.path.exists(ruta_anterior):
            os.remove(ruta_anterior)

    nombre = f'profesional_{current_user.id}.{extension}'
    archivo.seek(0)
    archivo.save(os.path.join(carpeta, nombre))
    return f'uploads/avatars/{nombre}'


@dashboard_bp.route('/ajustes', methods=['GET', 'POST'])
@login_required
@rol_requerido('profesional')
def ajustes():
    accion, form_perfil, form_password = _formularios_de_cuenta(PerfilProfesionalForm)

    if accion == 'actualizar_perfil' and form_perfil.validate_on_submit():
        archivo = request.files.get('foto')
        foto_valida = True
        if archivo and archivo.filename:
            try:
                current_user.foto = _guardar_foto(archivo)
            except ValueError as error:
                foto_valida = False
                flash(str(error), 'danger')
        if foto_valida:
            current_user.nombre = form_perfil.nombre.data
            current_user.apellido = form_perfil.apellido.data
            current_user.especialidad = form_perfil.especialidad.data or None
            current_user.numero_licencia = form_perfil.numero_licencia.data or None
            db.session.commit()
            registrar_actividad('editar', 'profesional', current_user.id)
            flash('Perfil actualizado correctamente.', 'success')
            return redirect(url_for('dashboard.ajustes'))
    if accion == 'cambiar_password' and _procesar_cambio_password(form_password):
        return redirect(url_for('dashboard.ajustes'))

    codigo = 400 if accion else 200
    return render_template('dashboard/ajustes.html', usuario=current_user,
                           form_perfil=form_perfil, form_password=form_password), codigo


@dashboard_bp.route('/modelo-ml')
@login_required
@rol_requerido('profesional', 'admin')
def modelo_ml():
    return render_template('ml/ficha.html', ficha=metadatos_modelo(), concordancia=concordancia_con_reglas(),
                           habilitado=current_app.config.get('ML_HABILITADO'))


# ---------------------------------------------------------------- Notificaciones (todos los roles)

def _enlace_notificacion(n):
    if n.recurso == 'solicitudes':
        return url_for('mensajes.solicitudes')
    if n.recurso == 'atencion' and n.recurso_id:
        return url_for('mensajes.conversacion', nino_id=n.recurso_id)
    if n.recurso == 'medicamentos' and n.recurso_id:
        return url_for('medicamentos.plan', nino_id=n.recurso_id)
    if n.recurso == 'mensajes' and n.recurso_id:
        return url_for('mensajes.conversacion', nino_id=n.recurso_id)
    if n.recurso == 'videollamada' and n.recurso_id:
        return url_for('videollamadas.sala', videollamada_id=n.recurso_id)
    return None


@dashboard_bp.route('/estado')
@login_required
def estado():
    """Contadores de notificaciones, alertas y solicitudes para actualizar la barra sin recargar, y la
    videollamada que esté sonando para el cuidador."""
    from app.services.notificaciones import contadores
    datos = contadores(current_user)
    if current_user.tipo_usuario == 'cuidador':
        from app.services.videollamadas import entrante_para
        llamada = entrante_para(current_user)
        if llamada is not None:
            datos['llamada'] = {
                'url': url_for('videollamadas.sala', videollamada_id=llamada.id),
                'texto': f'{llamada.profesional.nombre_con_titulo} te está llamando por video sobre '
                         f'{llamada.nino.nombre}.',
            }
    return jsonify(datos)


@dashboard_bp.route('/notificaciones')
@login_required
def notificaciones():
    lista = recientes(current_user)
    respuesta = render_template('dashboard/notificaciones.html', notificaciones=lista, enlace=_enlace_notificacion)
    marcar_todas_leidas(current_user)  # se marcan como leídas al mostrarlas
    return respuesta


# ---------------------------------------------------------------- Administrador

@dashboard_bp.route('/admin')
@login_required
@rol_requerido('admin')
def admin():
    return redirect(url_for('admin.inicio'))
