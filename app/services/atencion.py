"""Atención por mensajes con los profesionales de la clínica.

Flujo:
1. El cuidador envía una solicitud ("Conectando con un profesional de salud...").
2. La ven los profesionales DISPONIBLES con CUPO (casos abiertos < CUPO_CASOS_POR_PROFESIONAL).
3. El primero que la acepta atiende el caso (asignación atómica: nunca dos profesionales con el mismo caso).
4. El cuidador decide si autoriza a ese profesional a ver el expediente completo del niño/a.
5. El profesional cierra el caso cuando termina; la conversación queda para volver a comunicarse.

No es un canal de urgencias: ante signos de alarma la aplicación indica acudir a un servicio de salud.
"""
from flask import current_app

from app import db
from app.models import Autorizacion, Evaluacion, Mensaje, Profesional, SolicitudAtencion, ahora_utc
from app.services.acceso import autorizacion_vigente
from app.services.auditoria import registrar_actividad
from app.services.consentimiento import acceso_atencion_otorgado
from app.services.notificaciones import notificar


def cupo():
    return current_app.config['CUPO_CASOS_POR_PROFESIONAL']


def casos_abiertos(profesional_id):
    return SolicitudAtencion.query.filter_by(profesional_id=profesional_id, estado='asignada').count()


def puede_recibir(profesional):
    """Disponible, aprobado y con cupo libre."""
    return profesional.aprobado and profesional.disponible and casos_abiertos(profesional.id) < cupo()


def solicitud_abierta(nino_id):
    return (SolicitudAtencion.query.filter(SolicitudAtencion.nino_id == nino_id,
                                           SolicitudAtencion.estado.in_(('pendiente', 'asignada')))
            .order_by(SolicitudAtencion.id.desc()).first())


def pendientes():
    """Solicitudes sin atender: primero las de mayor nivel de riesgo, luego las más antiguas."""
    orden = {'rojo': 0, 'amarillo': 1, 'verde': 2}
    lista = SolicitudAtencion.query.filter_by(estado='pendiente').order_by(SolicitudAtencion.fecha_creacion).all()
    return sorted(lista, key=lambda s: orden.get(s.evaluacion.nivel_riesgo if s.evaluacion else None, 3))


def crear_solicitud(nino, cuidador, motivo):
    """Crea la solicitud (o devuelve la que ya está abierta) y avisa a los profesionales que pueden recibirla."""
    existente = solicitud_abierta(nino.id)
    if existente:
        return existente, False
    ultima = (Evaluacion.query.filter_by(nino_id=nino.id)
              .order_by(Evaluacion.fecha.desc(), Evaluacion.id.desc()).first())
    solicitud = SolicitudAtencion(nino_id=nino.id, cuidador_id=cuidador.id, motivo=motivo,
                                  evaluacion_id=ultima.id if ultima else None)
    db.session.add(solicitud)
    db.session.flush()
    nivel = f' (nivel {ultima.nivel_riesgo})' if ultima else ''
    for profesional in Profesional.query.filter_by(estado_aprobacion='aprobado', disponible=True).all():
        if casos_abiertos(profesional.id) < cupo():
            notificar(profesional.id, 'profesional', 'nueva_solicitud', 'Nueva solicitud de atención',
                      f'Un cuidador busca orientación para un niño/a de {nino.edad_texto()}{nivel}.',
                      'solicitudes', None)
    db.session.commit()
    registrar_actividad('solicitar_atencion', 'nino', nino.id, detalles={'solicitud_id': solicitud.id})
    return solicitud, True


def aceptar(solicitud_id, profesional):
    """Asigna la solicitud al profesional si sigue pendiente y él tiene cupo. Devuelve la solicitud o None."""
    if not puede_recibir(profesional):
        return None
    # UPDATE condicionado: si otro profesional la tomó un instante antes, no se asigna dos veces.
    tomadas = (SolicitudAtencion.query
               .filter_by(id=solicitud_id, estado='pendiente')
               .update({'estado': 'asignada', 'profesional_id': profesional.id, 'fecha_asignacion': ahora_utc()},
                       synchronize_session=False))
    if tomadas != 1:
        db.session.rollback()
        return None
    solicitud = db.session.get(SolicitudAtencion, solicitud_id)
    db.session.refresh(solicitud)
    # El motivo abre la conversación privada entre el cuidador y este profesional.
    db.session.add(Mensaje(nino_id=solicitud.nino_id, profesional_conversacion_id=profesional.id,
                           autor_tipo='cuidador', autor_cuidador_id=solicitud.cuidador_id, contenido=solicitud.motivo,
                           fecha=solicitud.fecha_creacion))
    notificar(solicitud.cuidador_id, 'cuidador', 'solicitud_asignada', 'Te conectaste con un profesional',
              f'{profesional.nombre_con_titulo} atenderá tu solicitud sobre {solicitud.nino.nombre}.',
              'atencion', solicitud.nino_id)
    db.session.commit()
    registrar_actividad('aceptar_solicitud', 'nino', solicitud.nino_id, detalles={'solicitud_id': solicitud.id})
    # Si el representante lo autorizó de antemano, el profesional recibe el expediente sin volver a preguntar.
    if acceso_atencion_otorgado(solicitud.nino):
        responder_acceso(solicitud, True, origen='autorizacion_previa')
    return solicitud


def responder_acceso(solicitud, otorga, origen='respuesta_del_cuidador'):
    """El cuidador decide si el profesional que lo atiende puede ver el expediente completo del niño/a."""
    solicitud.acceso = 'otorgado' if otorga else 'denegado'
    if otorga and not autorizacion_vigente(solicitud.nino_id, solicitud.profesional_id):
        db.session.add(Autorizacion(nino_id=solicitud.nino_id, profesional_id=solicitud.profesional_id, activa=True))
    db.session.commit()
    registrar_actividad('otorgar_acceso' if otorga else 'denegar_acceso', 'nino', solicitud.nino_id,
                        detalles={'profesional_id': solicitud.profesional_id, 'solicitud_id': solicitud.id,
                                  'origen': origen})


def cerrar(solicitud):
    solicitud.estado = 'cerrada'
    solicitud.fecha_cierre = ahora_utc()
    db.session.commit()
    registrar_actividad('cerrar_caso', 'nino', solicitud.nino_id, detalles={'solicitud_id': solicitud.id})


def cancelar(solicitud):
    solicitud.estado = 'cancelada'
    solicitud.fecha_cierre = ahora_utc()
    db.session.commit()
    registrar_actividad('cancelar_solicitud', 'nino', solicitud.nino_id, detalles={'solicitud_id': solicitud.id})


def hay_relacion(nino_id, profesional_id):
    """El profesional y el cuidador pueden conversar: autorización vigente o un caso (abierto o cerrado) entre ellos."""
    if autorizacion_vigente(nino_id, profesional_id):
        return True
    return SolicitudAtencion.query.filter(
        SolicitudAtencion.nino_id == nino_id, SolicitudAtencion.profesional_id == profesional_id,
        SolicitudAtencion.estado.in_(('asignada', 'cerrada')),
    ).first() is not None


def caso_abierto(nino_id, profesional_id):
    return SolicitudAtencion.query.filter_by(nino_id=nino_id, profesional_id=profesional_id,
                                             estado='asignada').first()
