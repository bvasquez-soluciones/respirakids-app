"""Operaciones del administrador. Solo trabaja con datos administrativos y agregados: nunca expone
la información clínica de un niño en particular."""
import secrets
import string
from datetime import timedelta

from sqlalchemy import func

from app import db
from app.models import (
    ConocimientoSanitario, Cuidador, Evaluacion, LogSeguridad, Nino, Profesional, SolicitudDerechos, ahora_utc,
)
from app.services.notificaciones import notificar

ESTADOS_PROFESIONAL = {
    'pendiente': 'Pendiente de aprobación',
    'aprobado': 'Aprobado',
    'suspendido': 'Suspendido',
    'rechazado': 'Rechazado',
}


def generar_password_temporal(longitud=12):
    """Contraseña aleatoria que cumple la política (letras y números)."""
    alfabeto = string.ascii_letters + string.digits
    while True:
        clave = ''.join(secrets.choice(alfabeto) for _ in range(longitud))
        if any(c.isalpha() for c in clave) and any(c.isdigit() for c in clave):
            return clave


def indicadores():
    """Cifras agregadas para el resumen del administrador."""
    hace_30_dias = ahora_utc() - timedelta(days=30)
    por_nivel = dict(
        db.session.query(Evaluacion.nivel_riesgo, func.count(Evaluacion.id))
        .filter(Evaluacion.fecha >= hace_30_dias).group_by(Evaluacion.nivel_riesgo).all()
    )
    profesionales = dict(
        db.session.query(Profesional.estado_aprobacion, func.count(Profesional.id))
        .group_by(Profesional.estado_aprobacion).all()
    )
    return {
        'cuidadores': Cuidador.query.filter_by(rol='cuidador').count(),
        'profesionales': profesionales,
        'ninos_activos': Nino.query.filter_by(estado='activo').count(),
        'ninos_sin_consentimiento': Nino.query.filter_by(estado='activo', consentimiento_otorgado=False).count(),
        'evaluaciones_30_dias': por_nivel,
        'solicitudes_pendientes': SolicitudDerechos.query.filter(
            SolicitudDerechos.estado.in_(('pendiente', 'en_tramite'))).count(),
        'cuentas_bloqueadas': (Cuidador.query.filter(Cuidador.bloqueado_hasta > ahora_utc()).count()
                               + Profesional.query.filter(Profesional.bloqueado_hasta > ahora_utc()).count()),
        'accesos_denegados_7_dias': LogSeguridad.query.filter(
            LogSeguridad.evento == 'acceso_denegado',
            LogSeguridad.timestamp >= ahora_utc() - timedelta(days=7)).count(),
        'conocimiento_activo': ConocimientoSanitario.query.filter_by(activo=True).count(),
    }


def crear_profesional(form):
    """Crea la cuenta (pendiente de aprobación) con contraseña temporal. Devuelve (profesional, clave)."""
    clave = generar_password_temporal()
    profesional = Profesional(
        nombre=form.nombre.data, apellido=form.apellido.data, correo=form.correo.data,
        telefono=form.telefono.data or None, tipo_documento=form.tipo_documento.data,
        numero_documento=form.numero_documento.data, profesion=form.profesion.data,
        especialidad=form.especialidad.data or None, tarjeta_profesional=form.tarjeta_profesional.data,
        registro_rethus=form.registro_rethus.data or None, rol='profesional',
        estado_aprobacion='pendiente', debe_cambiar_password=True,
    )
    profesional.set_password(clave)
    db.session.add(profesional)
    db.session.commit()
    return profesional, clave


def restablecer_password(profesional):
    clave = generar_password_temporal()
    profesional.set_password(clave)
    profesional.debe_cambiar_password = True
    profesional.intentos_fallidos = 0
    profesional.bloqueado_hasta = None
    db.session.commit()
    return clave


def cambiar_estado_profesional(profesional, estado):
    if estado not in ESTADOS_PROFESIONAL:
        raise ValueError(estado)
    profesional.estado_aprobacion = estado
    db.session.commit()


def desbloquear(usuario):
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    db.session.commit()


def responder_solicitud(solicitud, estado, respuesta):
    solicitud.estado = estado
    solicitud.respuesta = respuesta or solicitud.respuesta
    if estado in ('resuelta', 'rechazada'):
        solicitud.fecha_respuesta = ahora_utc()
    notificar(solicitud.usuario_id, solicitud.usuario_tipo, 'solicitud_derechos',
              'Actualización de tu solicitud de datos',
              f'Tu solicitud "{solicitud.tipo_texto}" está ahora: {estado.replace("_", " ")}.', 'privacidad', None)
    db.session.commit()
