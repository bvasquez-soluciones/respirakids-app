"""Supresión de datos personales por anonimización irreversible (Ley 1581 de 2012, art. 8 literal e y art. 15).

Qué hace con cada tipo de dato:
- ELIMINA: mensajes, consultas al asistente, notificaciones y copias versionadas de indicaciones (texto libre
  que puede contener nombres o detalles identificables).
- ANONIMIZA: nombres, apellidos, documentos, correo, teléfono, fotografía, notas y observaciones; la fecha de
  nacimiento se reduce al primer día del mes. Los niños quedan desvinculados del cuidador (cuidador_id vacío).
- CONSERVA, sin identificar a nadie: síntomas marcados, evaluaciones, seguimientos y medicamentos indicados
  (solo fines estadísticos), además del historial de consentimientos, la solicitud de supresión y los registros
  de seguridad, que son la prueba del cumplimiento legal.
La cuenta queda inutilizable: correo ficticio y contraseña aleatoria desconocida (que además invalida sus sesiones).

No hace commit: el llamador decide (permite revertir todo si algo falla).
"""
import os
import secrets

from flask import current_app

from app import db
from app.models import (
    ConsultaIA, Cuidador, Mensaje, MedicamentoRecetado, Notificacion, Profesional, Receta, SolicitudAtencion,
    VersionRegistro,
)

TEXTO_ANONIMO = 'Anonimizado'


def _correo_ficticio(usuario):
    # Dominio .invalid (RFC 2606): nunca recibe correo. Único por cuenta para respetar la restricción UNIQUE.
    return f'anonimizado-{usuario.tipo_usuario}-{usuario.id}@anonimizado.invalid'


def _inutilizar_acceso(usuario):
    usuario.correo = _correo_ficticio(usuario)
    usuario.set_password(secrets.token_urlsafe(48))  # nadie la conoce; cambia la huella y cierra sus sesiones
    usuario.token_recuperacion = None
    usuario.token_recuperacion_expira = None
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None


def _eliminar_notificaciones_de_nino(nino_id):
    """Notificaciones que mencionan al niño (a su cuidador y a los profesionales autorizados)."""
    Notificacion.query.filter(
        Notificacion.recurso.in_(('mensajes', 'medicamentos', 'atencion')), Notificacion.recurso_id == nino_id,
    ).delete(synchronize_session=False)


def anonimizar_nino(nino):
    """Anonimiza a un niño/a y su información asociada."""
    from app.services.adjuntos import eliminar_de_mensajes
    mensajes = Mensaje.query.filter_by(nino_id=nino.id).all()
    eliminar_de_mensajes(mensajes)  # fotos, documentos y notas de voz (archivo y registro)
    db.session.flush()
    Mensaje.query.filter_by(nino_id=nino.id).delete(synchronize_session=False)
    ConsultaIA.query.filter_by(nino_id=nino.id).delete(synchronize_session=False)
    _eliminar_notificaciones_de_nino(nino.id)

    for registro in nino.registros_sintomas:
        registro.observaciones = None
        registro.otros_sintomas = None
    for receta in Receta.query.filter_by(nino_id=nino.id).all():
        receta.motivo = None
        receta.indicaciones_generales = None
        VersionRegistro.query.filter_by(tabla='recetas', registro_id=receta.id).delete(synchronize_session=False)
        for medicamento in MedicamentoRecetado.query.filter_by(receta_id=receta.id).all():
            medicamento.instrucciones = None
            for toma in medicamento.tomas:
                toma.administrado_por_id = None
    for autorizacion in nino.autorizaciones:
        autorizacion.activa = False
    for solicitud in SolicitudAtencion.query.filter_by(nino_id=nino.id).all():
        solicitud.motivo = TEXTO_ANONIMO  # texto libre del cuidador
        solicitud.cuidador_id = None
        if solicitud.estado in ('pendiente', 'asignada'):
            solicitud.estado = 'cancelada'
    for seguimiento in nino.seguimientos:
        seguimiento.cuidador_id = None

    nino.nombre = TEXTO_ANONIMO
    nino.nombre_ficticio = TEXTO_ANONIMO
    nino.apellido = None
    nino.tipo_documento = None
    nino.numero_documento = None
    nino.fecha_nacimiento = nino.fecha_nacimiento.replace(day=1)  # conserva la edad aproximada (estadística)
    nino.consentimiento_ip = None
    nino.consentimiento_investigacion_ip = None
    nino.estado = 'anonimizado'
    nino.cuidador_id = None


def anonimizar_cuidador(cuidador):
    """Anonimiza la cuenta de un cuidador y la de todos sus niños/as."""
    if cuidador.rol == 'admin':
        raise ValueError('Una cuenta de administrador no se anonimiza: primero debe quitársele ese rol.')
    for nino in list(cuidador.ninos):
        anonimizar_nino(nino)
    ConsultaIA.query.filter_by(cuidador_id=cuidador.id).delete(synchronize_session=False)
    Notificacion.query.filter_by(usuario_tipo='cuidador', usuario_id=cuidador.id).delete(synchronize_session=False)

    _inutilizar_acceso(cuidador)
    cuidador.nombre = TEXTO_ANONIMO
    cuidador.apellido = None
    cuidador.telefono = None
    cuidador.tipo_documento = None
    cuidador.numero_documento = None
    cuidador.fecha_nacimiento = None
    cuidador.correo_verificado = False
    cuidador.token_verificacion = None
    cuidador.token_verificacion_expira = None


def anonimizar_profesional(profesional):
    """Anonimiza la cuenta de un profesional. Sus mensajes e indicaciones siguen en la historia de cada niño/a,
    firmados como 'Anonimizado'."""
    for autorizacion in profesional.autorizaciones:
        autorizacion.activa = False
    Notificacion.query.filter_by(usuario_tipo='profesional', usuario_id=profesional.id).delete(
        synchronize_session=False)
    if profesional.foto:
        ruta = os.path.join(current_app.root_path, 'static', profesional.foto)
        if os.path.isfile(ruta):
            os.remove(ruta)
        profesional.foto = None

    _inutilizar_acceso(profesional)
    profesional.nombre = TEXTO_ANONIMO
    profesional.apellido = None
    profesional.telefono = None
    profesional.tipo_documento = None
    profesional.numero_documento = None
    profesional.numero_licencia = None
    profesional.tarjeta_profesional = None
    profesional.registro_rethus = None
    profesional.estado_aprobacion = 'suspendido'
    profesional.debe_cambiar_password = False


def anonimizar_titular(usuario_tipo, usuario_id):
    """Anonimiza la cuenta completa de un titular. Devuelve el usuario anonimizado."""
    modelo = Cuidador if usuario_tipo == 'cuidador' else Profesional
    usuario = db.session.get(modelo, usuario_id)
    if usuario is None:
        raise ValueError('El titular no existe.')
    (anonimizar_cuidador if modelo is Cuidador else anonimizar_profesional)(usuario)
    return usuario


def esta_anonimizado(usuario):
    return usuario.correo.endswith('@anonimizado.invalid')
