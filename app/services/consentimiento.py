"""Registro y consulta de consentimientos.

Cada otorgamiento o revocación crea una fila nueva en `consentimientos` (historial
inmutable). Las columnas `consentimiento_*` de la tabla `ninos` reflejan el estado vigente.
"""
from flask import current_app, has_request_context, request

from app import db
from app.models import Consentimiento, ahora_utc
from app.models.privacidad import (
    ACCESO_ATENCION_NINO, INVESTIGACION_NINO, POLITICA_DATOS, TERMINOS_USO, TRATAMIENTO_NINO,
)


def _contexto():
    if not has_request_context():
        return None, None
    return request.remote_addr, (request.user_agent.string or '')[:500]


def _registrar(usuario, tipo, otorgado, nino=None, version=None):
    ip, user_agent = _contexto()
    consentimiento = Consentimiento(
        usuario_id=usuario.id, usuario_tipo=usuario.tipo_usuario,
        nino_id=nino.id if nino else None, tipo=tipo, otorgado=otorgado,
        version_politica=version or current_app.config['POLITICA_VERSION'], ip=ip, user_agent=user_agent,
    )
    db.session.add(consentimiento)
    return consentimiento


def _vigente(usuario, tipo, version):
    ultimo = (
        Consentimiento.query
        .filter_by(usuario_id=usuario.id, usuario_tipo=usuario.tipo_usuario, tipo=tipo)
        .order_by(Consentimiento.fecha.desc(), Consentimiento.id.desc())
        .first()
    )
    return bool(ultimo and ultimo.otorgado and ultimo.version_politica == version)


def politica_aceptada(usuario):
    """True si el usuario aceptó la versión vigente de la política de tratamiento de datos."""
    return _vigente(usuario, POLITICA_DATOS, current_app.config['POLITICA_VERSION'])


def terminos_aceptados(usuario):
    """True si el usuario aceptó la versión vigente de los términos y condiciones de uso."""
    return _vigente(usuario, TERMINOS_USO, current_app.config['TERMINOS_VERSION'])


def documentos_aceptados(usuario):
    """La política y los términos vigentes: requisito para usar la plataforma."""
    return politica_aceptada(usuario) and terminos_aceptados(usuario)


def aceptar_politica(usuario):
    """Registra la aceptación de la política y de los términos vigentes (cada uno con su versión)."""
    _registrar(usuario, POLITICA_DATOS, True)
    _registrar(usuario, TERMINOS_USO, True, version=current_app.config['TERMINOS_VERSION'])


def acceso_atencion_otorgado(nino):
    """True si el representante autorizó de antemano que el profesional que atienda una solicitud vea el
    expediente completo (y sigue vigente la autorización de tratamiento de datos de salud)."""
    if not nino.consentimiento_otorgado:
        return False
    ultimo = (Consentimiento.query.filter_by(nino_id=nino.id, tipo=ACCESO_ATENCION_NINO)
              .order_by(Consentimiento.fecha.desc(), Consentimiento.id.desc()).first())
    return bool(ultimo and ultimo.otorgado)


def registrar_consentimiento_nino(usuario, nino, tratamiento, investigacion, atencion=None):
    """Registra la autorización del representante sobre los datos del niño y actualiza su estado vigente."""
    ip, _ = _contexto()
    ahora = ahora_utc()

    if tratamiento != nino.consentimiento_otorgado or nino.consentimiento_fecha is None:
        _registrar(usuario, TRATAMIENTO_NINO, tratamiento, nino)
        nino.consentimiento_otorgado = tratamiento
        nino.consentimiento_fecha = ahora
        nino.consentimiento_ip = ip

    if investigacion != nino.consentimiento_investigacion_otorgado or nino.consentimiento_investigacion_fecha is None:
        _registrar(usuario, INVESTIGACION_NINO, investigacion, nino)
        nino.consentimiento_investigacion_otorgado = investigacion
        nino.consentimiento_investigacion_fecha = ahora
        nino.consentimiento_investigacion_ip = ip

    if atencion is not None:
        previo = (Consentimiento.query.filter_by(nino_id=nino.id, tipo=ACCESO_ATENCION_NINO)
                  .order_by(Consentimiento.fecha.desc(), Consentimiento.id.desc()).first())
        # Sin registro previo equivale a "no autorizado": solo se guarda al otorgarla o al retirarla.
        if (previo.otorgado if previo else False) != atencion:
            _registrar(usuario, ACCESO_ATENCION_NINO, atencion, nino)


def historial_consentimientos(usuario):
    return (
        Consentimiento.query
        .filter_by(usuario_id=usuario.id, usuario_tipo=usuario.tipo_usuario)
        .order_by(Consentimiento.fecha.desc(), Consentimiento.id.desc())
        .all()
    )
