"""Panel del administrador. Todas las rutas exigen rol 'admin' (ver exigir_administrador).

El administrador gestiona cuentas, solicitudes de derechos, catálogos y auditoría, pero no accede a la
información clínica individual de los niños.
"""
import os
from datetime import date, datetime, time

from flask import abort, current_app, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user

from app import db
from app.admin import admin_bp
from app.asistente.conocimiento import SOLO_PROFESIONAL, importar_documento
from app.clinica import reglas_v1
from app.clinica.motor import version_vigente
from app.fechas import a_local, a_utc
from app.forms import ProfesionalAdminForm, ResponderSolicitudForm
from app.ml.prediccion import concordancia_con_reglas, metadatos_modelo
from app.models import (
    ConocimientoSanitario, Cuidador, LogActividad, LogSeguridad, Profesional, SolicitudDerechos, ahora_utc,
)
from app.services.administracion import (
    ESTADOS_PROFESIONAL, cambiar_estado_profesional, crear_profesional, desbloquear, indicadores,
    responder_solicitud, restablecer_password,
)
from app.services.auditoria import registrar_actividad
from app.services.plazos import dias_restantes, fecha_limite

POR_PAGINA = 25
CAMPOS_RESPONSABLE = ('RESPONSABLE_NOMBRE', 'RESPONSABLE_ID', 'RESPONSABLE_DIRECCION',
                      'RESPONSABLE_CORREO', 'RESPONSABLE_TELEFONO')


@admin_bp.before_request
def exigir_administrador():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.full_path))
    if current_user.rol != 'admin':
        abort(403)
    return None


def _sin_cache(contenido):
    """Las páginas que muestran contraseñas temporales no deben quedar en la caché del navegador."""
    respuesta = make_response(contenido)
    respuesta.headers['Cache-Control'] = 'no-store'
    return respuesta


def _hoy_local():
    return a_local(ahora_utc()).date()


def _buscar(consulta, modelo, texto):
    patron = f'%{texto}%'
    return consulta.filter(modelo.nombre.ilike(patron) | modelo.apellido.ilike(patron) | modelo.correo.ilike(patron))


# ---------------------------------------------------------------- Resumen

@admin_bp.route('/')
def inicio():
    return render_template('admin/inicio.html', datos=indicadores(), version_reglas=version_vigente())


# ---------------------------------------------------------------- Profesionales

@admin_bp.route('/profesionales')
def profesionales():
    estado = request.args.get('estado', '')
    busqueda = request.args.get('q', '').strip()
    consulta = Profesional.query
    if estado in ESTADOS_PROFESIONAL:
        consulta = consulta.filter_by(estado_aprobacion=estado)
    if busqueda:
        consulta = _buscar(consulta, Profesional, busqueda)
    pagina = consulta.order_by(Profesional.fecha_registro.desc()).paginate(
        page=request.args.get('pagina', 1, type=int), per_page=POR_PAGINA, error_out=False)
    return render_template('admin/profesionales.html', pagina=pagina, estado=estado, busqueda=busqueda,
                           estados=ESTADOS_PROFESIONAL)


@admin_bp.route('/profesionales/nuevo', methods=['GET', 'POST'])
def nuevo_profesional():
    form = ProfesionalAdminForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            existe = (Profesional.query.filter_by(correo=form.correo.data).first()
                      or Cuidador.query.filter_by(correo=form.correo.data).first())
            if existe:
                form.correo.errors.append('Ya existe una cuenta con ese correo.')
            else:
                profesional, clave = crear_profesional(form)
                registrar_actividad('crear_profesional', 'profesional', profesional.id)
                return _sin_cache(render_template('admin/clave_temporal.html', profesional=profesional,
                                                  clave=clave, accion='creada'))
        return render_template('admin/profesional_nuevo.html', form=form), 400
    return render_template('admin/profesional_nuevo.html', form=form)


@admin_bp.route('/profesionales/<int:profesional_id>/estado', methods=['POST'])
def estado_profesional(profesional_id):
    profesional = db.session.get(Profesional, profesional_id) or abort(404)
    estado = request.form.get('estado')
    if estado not in ESTADOS_PROFESIONAL:
        abort(400)
    cambiar_estado_profesional(profesional, estado)
    registrar_actividad('cambiar_estado_profesional', 'profesional', profesional.id, detalles={'estado': estado})
    flash(f'{profesional.nombre_completo}: {ESTADOS_PROFESIONAL[estado].lower()}.', 'success')
    return redirect(url_for('admin.profesionales'))


@admin_bp.route('/profesionales/<int:profesional_id>/restablecer', methods=['POST'])
def restablecer_profesional(profesional_id):
    profesional = db.session.get(Profesional, profesional_id) or abort(404)
    clave = restablecer_password(profesional)
    registrar_actividad('restablecer_password', 'profesional', profesional.id)
    return _sin_cache(render_template('admin/clave_temporal.html', profesional=profesional, clave=clave,
                                      accion='restablecida'))


# ---------------------------------------------------------------- Cuidadores

@admin_bp.route('/cuidadores')
def cuidadores():
    busqueda = request.args.get('q', '').strip()
    consulta = Cuidador.query
    if busqueda:
        consulta = _buscar(consulta, Cuidador, busqueda)
    pagina = consulta.order_by(Cuidador.fecha_registro.desc()).paginate(
        page=request.args.get('pagina', 1, type=int), per_page=POR_PAGINA, error_out=False)
    return render_template('admin/cuidadores.html', pagina=pagina, busqueda=busqueda)


@admin_bp.route('/usuarios/<tipo>/<int:usuario_id>/desbloquear', methods=['POST'])
def desbloquear_usuario(tipo, usuario_id):
    modelo = {'cuidador': Cuidador, 'profesional': Profesional}.get(tipo) or abort(404)
    usuario = db.session.get(modelo, usuario_id) or abort(404)
    desbloquear(usuario)
    registrar_actividad('desbloquear_cuenta', tipo, usuario.id)
    flash(f'Cuenta de {usuario.nombre_completo} desbloqueada.', 'success')
    return redirect(url_for('admin.cuidadores' if tipo == 'cuidador' else 'admin.profesionales'))


# ---------------------------------------------------------------- Solicitudes de derechos

def _titular(solicitud):
    modelo = Cuidador if solicitud.usuario_tipo == 'cuidador' else Profesional
    return db.session.get(modelo, solicitud.usuario_id)


@admin_bp.route('/solicitudes')
def solicitudes():
    estado = request.args.get('estado', 'abiertas')
    consulta = SolicitudDerechos.query
    if estado == 'abiertas':
        consulta = consulta.filter(SolicitudDerechos.estado.in_(('pendiente', 'en_tramite')))
    elif estado:
        consulta = consulta.filter_by(estado=estado)
    return render_template(
        'admin/solicitudes.html', solicitudes=consulta.order_by(SolicitudDerechos.fecha_solicitud).all(),
        estado=estado, hoy=_hoy_local(), fecha_limite=fecha_limite, dias_restantes=dias_restantes, titular=_titular,
    )


@admin_bp.route('/solicitudes/<int:solicitud_id>', methods=['GET', 'POST'])
def solicitud(solicitud_id):
    item = db.session.get(SolicitudDerechos, solicitud_id) or abort(404)
    form = ResponderSolicitudForm(obj=item if request.method == 'GET' else None)
    if request.method == 'POST' and form.validate_on_submit():
        responder_solicitud(item, form.estado.data, form.respuesta.data)
        registrar_actividad('responder_solicitud_derechos', 'solicitud_derechos', item.id,
                            detalles={'estado': item.estado})
        flash('Solicitud actualizada. El titular fue notificado.', 'success')
        return redirect(url_for('admin.solicitudes'))
    codigo = 400 if request.method == 'POST' else 200
    return render_template('admin/solicitud.html', solicitud=item, form=form, titular=_titular(item),
                           limite=fecha_limite(item), restantes=dias_restantes(item, _hoy_local())), codigo


# ---------------------------------------------------------------- Auditoría

@admin_bp.route('/auditoria')
def auditoria():
    tipo = 'actividad' if request.args.get('tipo') == 'actividad' else 'seguridad'
    modelo = LogActividad if tipo == 'actividad' else LogSeguridad
    campo_evento = modelo.accion if tipo == 'actividad' else modelo.evento
    evento = request.args.get('evento', '').strip()
    usuario_tipo = request.args.get('usuario_tipo', '')
    desde_texto = request.args.get('desde', '')

    consulta = modelo.query
    if evento:
        consulta = consulta.filter(campo_evento == evento)
    if usuario_tipo in ('cuidador', 'profesional'):
        consulta = consulta.filter(modelo.usuario_tipo == usuario_tipo)
    try:
        desde = date.fromisoformat(desde_texto) if desde_texto else None
    except ValueError:
        desde = None
    if desde:
        consulta = consulta.filter(modelo.timestamp >= a_utc(datetime.combine(desde, time.min)))

    pagina = consulta.order_by(modelo.timestamp.desc()).paginate(
        page=request.args.get('pagina', 1, type=int), per_page=50, error_out=False)
    eventos = [e for (e,) in db.session.query(campo_evento).distinct().order_by(campo_evento)]
    return render_template('admin/auditoria.html', pagina=pagina, tipo=tipo, evento=evento, eventos=eventos,
                           usuario_tipo=usuario_tipo, desde=desde_texto)


# ---------------------------------------------------------------- Catálogos

@admin_bp.route('/conocimiento')
def conocimiento():
    filtro = request.args.get('filtro', 'activos')
    consulta = ConocimientoSanitario.query
    if filtro == 'activos':
        consulta = consulta.filter_by(activo=True)
    elif filtro == 'inactivos':
        consulta = consulta.filter(ConocimientoSanitario.activo.isnot(True))
    entradas = consulta.order_by(ConocimientoSanitario.categoria, ConocimientoSanitario.titulo).all()
    return render_template('admin/conocimiento.html', entradas=entradas, filtro=filtro,
                           SOLO_PROFESIONAL=SOLO_PROFESIONAL)


@admin_bp.route('/conocimiento/<int:entrada_id>/activo', methods=['POST'])
def alternar_conocimiento(entrada_id):
    entrada = db.session.get(ConocimientoSanitario, entrada_id) or abort(404)
    entrada.activo = not entrada.activo
    db.session.commit()
    registrar_actividad('alternar_conocimiento', 'conocimiento', entrada.id, detalles={'activo': entrada.activo})
    flash(f'"{entrada.titulo}" {"activado" if entrada.activo else "desactivado"}.', 'success')
    return redirect(url_for('admin.conocimiento', filtro=request.args.get('filtro', 'activos')))


@admin_bp.route('/conocimiento/importar', methods=['POST'])
def reimportar_conocimiento():
    resumen = importar_documento()
    registrar_actividad('importar_conocimiento', 'conocimiento', None, detalles={
        'fragmentos': resumen['fragmentos'], 'ids_activos_antes_de_importar': resumen['activos_previos']})
    flash(f'Documento maestro importado: {resumen["fragmentos"]} fragmentos activos.', 'success')
    return redirect(url_for('admin.conocimiento'))


@admin_bp.route('/reglas')
def reglas():
    return render_template('admin/reglas.html', reglas=reglas_v1.REGLAS,
                           no_implementables=reglas_v1.NO_IMPLEMENTABLES, version=reglas_v1.VERSION,
                           version_vigente=version_vigente(),
                           validadas=os.environ.get('REGLAS_CLINICAS_VALIDADAS') == reglas_v1.VERSION)


@admin_bp.route('/modelo-ml')
def modelo_ml():
    return render_template('admin/modelo_ml.html', ficha=metadatos_modelo(), concordancia=concordancia_con_reglas(),
                           habilitado=current_app.config.get('ML_HABILITADO'))


# ---------------------------------------------------------------- Configuración (solo lectura)

@admin_bp.route('/configuracion')
def configuracion():
    cfg = current_app.config
    validadas = os.environ.get('REGLAS_CLINICAS_VALIDADAS')
    responsable_completo = not any(str(cfg[c]).startswith('[') for c in CAMPOS_RESPONSABLE)
    estado = [
        # (concepto, valor, ¿está bien?: True / False / None = informativo)
        ('Entorno', os.environ.get('RESPIRAKIDS_ENV', 'development'), None),
        ('Reglas clínicas activas', cfg.get('MOTOR_CLINICO_VERSION'), None),
        ('Reglas validadas por un profesional de salud', validadas or 'No',
         validadas == cfg.get('MOTOR_CLINICO_VERSION')),
        ('Modelo ML complementario', 'Activado' if cfg.get('ML_HABILITADO') else 'Desactivado', None),
        ('Asistente IA: clave configurada', 'Sí' if cfg.get('GEMINI_API_KEY') else 'No', bool(cfg.get('GEMINI_API_KEY'))),
        ('Asistente IA: modelo', cfg.get('GEMINI_MODEL'), None),
        ('Versión de la política de datos', cfg.get('POLITICA_VERSION'), None),
        ('Datos del responsable del tratamiento', 'Completos' if responsable_completo else 'Incompletos',
         responsable_completo),
        ('Zona horaria', cfg.get('ZONA_HORARIA'), None),
        ('HTTPS obligatorio', 'Sí' if cfg.get('FORCE_HTTPS') else 'No', None),
        ('Almacenamiento del límite de peticiones', cfg.get('RATELIMIT_STORAGE_URI'), None),
    ]
    return render_template('admin/configuracion.html', estado=estado)
