"""Videollamadas entre el profesional que atiende un caso y el cuidador (telemedicina, sin grabación).

Flujo: el profesional la inicia dentro de su caso abierto -> el cuidador recibe el aviso ("llamando") -> acepta
dando su consentimiento -> "en_curso" -> cualquiera cuelga -> "finalizada". Sin respuesta a tiempo queda "perdida".

El video viaja directamente entre los dos navegadores (WebRTC, cifrado). El servidor solo intercambia los
mensajes técnicos para conectarlos (SenalVideollamada), que se borran al terminar, y guarda el registro mínimo:
quién, cuándo, cuánto duró y el consentimiento. Nada de imagen ni sonido pasa por aquí ni se guarda.
"""
import base64
import hashlib
import hmac
import json
import time
from datetime import timedelta

from flask import current_app

from app import db
from app.models import Mensaje, SenalVideollamada, SolicitudAtencion, Videollamada, ahora_utc
from app.services.auditoria import registrar_actividad
from app.services.notificaciones import notificar

TIPOS_SENAL = ('oferta', 'respuesta', 'candidato')
TAMANO_MAXIMO_SENAL = 20000  # caracteres: una oferta SDP normal ocupa unos pocos miles


class VideollamadaNoPermitida(Exception):
    """La acción no corresponde al estado de la llamada o del caso."""


def servidores_ice(identidad):
    """Servidores STUN/TURN para el navegador. Las credenciales TURN son temporales (coturn `use-auth-secret`)."""
    cfg = current_app.config
    servidores = [{'urls': cfg['WEBRTC_STUN_URLS']}] if cfg['WEBRTC_STUN_URLS'] else []
    if cfg['TURN_URLS'] and cfg['TURN_SECRETO']:
        usuario = f'{int(time.time()) + cfg["TURN_VIGENCIA_SEGUNDOS"]}:{identidad}'
        firma = hmac.new(cfg['TURN_SECRETO'].encode(), usuario.encode(), hashlib.sha1).digest()
        servidores.append({'urls': cfg['TURN_URLS'], 'username': usuario,
                           'credential': base64.b64encode(firma).decode()})
    return servidores


def activa_del_caso(solicitud_id):
    llamada = (Videollamada.query.filter(Videollamada.solicitud_id == solicitud_id,
                                         Videollamada.estado.in_(Videollamada.ESTADOS_ACTIVOS))
               .order_by(Videollamada.id.desc()).first())
    if llamada is not None:
        actualizar_vencida(llamada)
    return llamada if llamada is not None and llamada.activa else None


def iniciar(solicitud, profesional):
    """El profesional llama al cuidador. Solo dentro de su propio caso abierto."""
    if solicitud.estado != 'asignada' or solicitud.profesional_id != profesional.id or solicitud.cuidador_id is None:
        raise VideollamadaNoPermitida('Solo puedes llamar dentro de un caso abierto que tú atiendes.')
    existente = activa_del_caso(solicitud.id)
    if existente is not None:
        return existente
    llamada = Videollamada(solicitud_id=solicitud.id, nino_id=solicitud.nino_id, profesional_id=profesional.id,
                           cuidador_id=solicitud.cuidador_id, estado='llamando', pulso_profesional=ahora_utc())
    db.session.add(llamada)
    db.session.flush()
    notificar(solicitud.cuidador_id, 'cuidador', 'videollamada', 'Videollamada entrante',
              f'{profesional.nombre_con_titulo} te está llamando por video sobre {solicitud.nino.nombre}.',
              'videollamada', llamada.id)
    db.session.commit()
    registrar_actividad('iniciar_videollamada', 'nino', llamada.nino_id, detalles={'videollamada_id': llamada.id})
    return llamada


def _terminar(llamada, estado):
    llamada.estado = estado
    llamada.fecha_fin = ahora_utc()
    SenalVideollamada.query.filter_by(videollamada_id=llamada.id).delete(synchronize_session=False)
    # Queda constancia en la conversación (sin contenido de la llamada: solo el resultado y la duración).
    if estado == 'finalizada':
        minutos, segundos = divmod(llamada.duracion_segundos, 60)
        texto = f'📹 Videollamada finalizada · duración {minutos} min {segundos:02d} s.'
    elif estado == 'perdida':
        texto = '📹 Videollamada perdida: no fue contestada.'
    elif estado == 'rechazada':
        texto = '📹 Videollamada no aceptada por el cuidador.'
    else:
        texto = None
    if texto:
        db.session.add(Mensaje(nino_id=llamada.nino_id, profesional_conversacion_id=llamada.profesional_id,
                               autor_tipo='profesional', autor_profesional_id=llamada.profesional_id, contenido=texto))
    db.session.commit()
    registrar_actividad('terminar_videollamada', 'nino', llamada.nino_id,
                        detalles={'videollamada_id': llamada.id, 'estado': estado,
                                  'duracion_segundos': llamada.duracion_segundos})


def actualizar_vencida(llamada):
    """Llamada sin contestar a tiempo -> perdida; en curso sin señal de vida de un lado -> finalizada."""
    if not llamada.activa:
        return llamada
    ahora = ahora_utc()
    cfg = current_app.config
    if llamada.estado == 'llamando' and ahora - llamada.fecha_creacion > timedelta(
            seconds=cfg['VIDEOLLAMADA_TIMBRE_SEGUNDOS']):
        _terminar(llamada, 'perdida')
    elif llamada.estado == 'en_curso':
        limite = ahora - timedelta(seconds=cfg['VIDEOLLAMADA_SIN_PULSO_SEGUNDOS'])
        if any(p is None or p < limite for p in (llamada.pulso_profesional, llamada.pulso_cuidador)):
            _terminar(llamada, 'finalizada')
    return llamada


def responder(llamada, acepta, consentimiento):
    """El cuidador contesta (con su consentimiento para la atención por video) o rechaza."""
    actualizar_vencida(llamada)
    if llamada.estado != 'llamando':
        raise VideollamadaNoPermitida('La llamada ya no está disponible.')
    if not acepta:
        _terminar(llamada, 'rechazada')
        return llamada
    if not consentimiento:
        raise VideollamadaNoPermitida('Para contestar debes aceptar la atención por videollamada.')
    ahora = ahora_utc()
    llamada.estado = 'en_curso'
    llamada.fecha_respuesta = ahora
    llamada.consentimiento_fecha = ahora
    llamada.pulso_cuidador = ahora
    llamada.pulso_profesional = ahora
    db.session.commit()
    registrar_actividad('aceptar_videollamada', 'nino', llamada.nino_id,
                        detalles={'videollamada_id': llamada.id, 'consentimiento': True})
    return llamada


def colgar(llamada, rol):
    if not llamada.activa:
        return llamada
    if llamada.estado == 'llamando':
        _terminar(llamada, 'cancelada' if rol == 'profesional' else 'rechazada')
    else:
        _terminar(llamada, 'finalizada')
    return llamada


def terminar_del_caso(solicitud_id):
    """Al cerrar un caso se cuelga cualquier llamada que siga activa."""
    llamada = activa_del_caso(solicitud_id)
    if llamada is not None:
        colgar(llamada, 'profesional')


def latido(llamada, rol):
    if llamada.activa:
        setattr(llamada, f'pulso_{rol}', ahora_utc())
        db.session.commit()


def agregar_senal(llamada, rol, tipo, datos):
    if not llamada.activa:
        raise VideollamadaNoPermitida('La llamada terminó.')
    if tipo not in TIPOS_SENAL:
        raise ValueError('Tipo de señal no válido.')
    texto = json.dumps(datos, separators=(',', ':'))
    if len(texto) > TAMANO_MAXIMO_SENAL:
        raise ValueError('Señal demasiado grande.')
    senal = SenalVideollamada(videollamada_id=llamada.id, emisor=rol, tipo=tipo, datos=texto)
    db.session.add(senal)
    db.session.commit()
    return senal


def senales_para(llamada, rol, desde):
    """Señales de la otra parte posteriores a `desde`."""
    return (SenalVideollamada.query
            .filter(SenalVideollamada.videollamada_id == llamada.id, SenalVideollamada.emisor != rol,
                    SenalVideollamada.id > desde)
            .order_by(SenalVideollamada.id).all())


def entrante_para(cuidador):
    """Llamada que está sonando para este cuidador (o None)."""
    llamada = (Videollamada.query.filter_by(cuidador_id=cuidador.id, estado='llamando')
               .order_by(Videollamada.id.desc()).first())
    if llamada is not None:
        actualizar_vencida(llamada)
    return llamada if llamada is not None and llamada.estado == 'llamando' else None


def caso_de(solicitud_id):
    return db.session.get(SolicitudAtencion, solicitud_id)
