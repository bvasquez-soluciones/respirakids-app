import json

from flask import Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db, limiter
from app.forms import AceptarPoliticaForm, SolicitudDerechosForm
from app.models import SolicitudDerechos
from app.privacidad import privacidad_bp
from app.services.acceso import es_cuidador
from app.services.auditoria import registrar_actividad
from app.services.consentimiento import aceptar_politica, documentos_aceptados, historial_consentimientos
from app.services.datos_titular import exportar_datos_cuidador, exportar_datos_profesional

# Rutas disponibles aunque el usuario aún no haya aceptado la política vigente.
ENDPOINTS_LIBRES = {'static', 'home', 'privacidad.politica', 'privacidad.terminos', 'privacidad.aceptar',
                    'auth.logout', 'sistema.salud', 'auth.verificar_correo', 'auth.restablecer',
                    'ayuda.indice', 'ayuda.cuidadores', 'ayuda.profesionales'}


@privacidad_bp.before_app_request
def exigir_politica_vigente():
    if not current_user.is_authenticated or request.endpoint in ENDPOINTS_LIBRES or request.endpoint is None:
        return None
    if documentos_aceptados(current_user):
        return None
    if request.is_json or request.path.startswith('/asistente/preguntar'):
        return {'error': 'Debes aceptar la política de datos y los términos de uso vigentes para continuar.'}, 403
    return redirect(url_for('privacidad.aceptar', next=request.full_path if request.method == 'GET' else None))


@privacidad_bp.route('/')
def politica():
    return render_template('privacidad/politica.html')


@privacidad_bp.route('/terminos')
def terminos():
    return render_template('privacidad/terminos.html')


@privacidad_bp.route('/aceptar', methods=['GET', 'POST'])
@login_required
def aceptar():
    form = AceptarPoliticaForm()
    if request.method == 'POST':
        if not form.validate_on_submit():
            return render_template('privacidad/aceptar.html', form=form), 400
        aceptar_politica(current_user)
        db.session.commit()
        registrar_actividad('aceptar_politica', 'politica', None)
        flash('Gracias. Registramos tu aceptación de la política de datos y de los términos de uso.', 'success')

        destino = request.args.get('next', '')
        if destino.startswith('/') and not destino.startswith('//'):
            return redirect(destino)
        return redirect(url_for('home'))

    return render_template('privacidad/aceptar.html', form=form)


def _ninos_del_usuario():
    return sorted(current_user.ninos, key=lambda n: n.nombre) if es_cuidador() else []


@privacidad_bp.route('/mis-datos')
@login_required
def mis_datos():
    return _render_mis_datos(SolicitudDerechosForm(ninos=_ninos_del_usuario()))


def _render_mis_datos(form):
    ninos = _ninos_del_usuario()
    solicitudes = (
        SolicitudDerechos.query
        .filter_by(usuario_id=current_user.id, usuario_tipo=current_user.tipo_usuario)
        .order_by(SolicitudDerechos.fecha_solicitud.desc())
        .all()
    )
    return render_template(
        'privacidad/mis_datos.html', ninos=ninos, solicitudes=solicitudes,
        consentimientos=historial_consentimientos(current_user), form=form,
    )


@privacidad_bp.route('/mis-datos/exportar')
@login_required
@limiter.limit('10 per hour')
def exportar():
    if es_cuidador():
        datos = exportar_datos_cuidador(current_user)
    else:
        datos = exportar_datos_profesional(current_user)
    registrar_actividad('exportar_datos_titular', current_user.tipo_usuario, current_user.id)
    contenido = json.dumps(datos, ensure_ascii=False, indent=2)
    return Response(
        contenido, mimetype='application/json',
        headers={'Content-Disposition': 'attachment; filename=mis_datos_respirakids.json'},
    )


@privacidad_bp.route('/solicitudes', methods=['POST'])
@login_required
@limiter.limit('10 per day')
def crear_solicitud():
    form = SolicitudDerechosForm(ninos=_ninos_del_usuario())
    if not form.validate_on_submit():
        return _render_mis_datos(form), 400

    solicitud = SolicitudDerechos(
        usuario_id=current_user.id, usuario_tipo=current_user.tipo_usuario,
        nino_id=form.nino_id.data or None, tipo=form.tipo.data,
        descripcion=form.descripcion.data,
    )
    db.session.add(solicitud)
    db.session.commit()
    registrar_actividad('crear_solicitud_derechos', 'solicitud_derechos', solicitud.id,
                        detalles={'tipo': solicitud.tipo, 'nino_id': solicitud.nino_id})
    flash('Tu solicitud fue registrada. Recibirás respuesta dentro de los plazos legales.', 'success')
    return redirect(url_for('privacidad.mis_datos'))
