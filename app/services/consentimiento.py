"""Registro y consulta de consentimientos.

Cada otorgamiento o revocación crea una fila nueva en `consentimientos` (historial
inmutable). Las columnas `consentimiento_*` de la tabla `ninos` reflejan el estado vigente.
"""
from flask import current_app, has_request_context, request

from app import db
from app.models import Consentimiento, ahora_utc
from app.models.privacidad import INVESTIGACION_NINO, POLITICA_DATOS, TRATAMIENTO_NINO


def _contexto():
    if not has_request_context():
        return None, None
    return request.remote_addr, (request.user_agent.string or '')[:500]


def _registrar(usuario, tipo, otorgado, nino=None):
    ip, user_agent = _contexto()
    consentimiento = Consentimiento(
        usuario_id=usuario.id, usuario_tipo=usuario.tipo_usuario,
        nino_id=nino.id if nino else None, tipo=tipo, otorgado=otorgado,
        version_politica=current_app.config['POLITICA_VERSION'], ip=ip, user_agent=user_agent,
    )
    db.session.add(consentimiento)
    return consentimiento


def politica_aceptada(usuario):
    """True si el usuario aceptó la versión vigente de la política de tratamiento de datos."""
    ultimo = (
        Consentimiento.query
        .filter_by(usuario_id=usuario.id, usuario_tipo=usuario.tipo_usuario, tipo=POLITICA_DATOS)
        .order_by(Consentimiento.fecha.desc(), Consentimiento.id.desc())
        .first()
    )
    return bool(ultimo and ultimo.otorgado and ultimo.version_politica == current_app.config['POLITICA_VERSION'])


def aceptar_politica(usuario):
    _registrar(usuario, POLITICA_DATOS, True)


def registrar_consentimiento_nino(usuario, nino, tratamiento, investigacion):
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


def historial_consentimientos(usuario):
    return (
        Consentimiento.query
        .filter_by(usuario_id=usuario.id, usuario_tipo=usuario.tipo_usuario)
        .order_by(Consentimiento.fecha.desc(), Consentimiento.id.desc())
        .all()
    )
