"""Derecho de acceso: exportación de todos los datos personales de un cuidador y sus niños."""
from datetime import date, datetime

from flask import current_app

from app.models import ConsultaIA, Mensaje, SolicitudAtencion, SolicitudDerechos
from app.services.consentimiento import historial_consentimientos

# Campos que nunca se exportan (secretos de la cuenta).
CAMPOS_EXCLUIDOS = {
    'password_hash', 'token_verificacion', 'token_verificacion_expira',
    'token_recuperacion', 'token_recuperacion_expira', 'nombre_ficticio',
}


def _serializar(valor):
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    return valor


def _fila(objeto, excluir=()):
    columnas = objeto.__table__.columns.keys()
    return {
        c: _serializar(getattr(objeto, c))
        for c in columnas if c not in CAMPOS_EXCLUIDOS and c not in excluir
    }


def exportar_datos_cuidador(cuidador):
    ninos = []
    for nino in cuidador.ninos:
        registros = sorted(nino.registros_sintomas, key=lambda r: r.fecha or datetime.min)
        ninos.append({
            'datos': _fila(nino),
            'condiciones_de_base': [_fila(p) for p in nino.patologias_base],
            'registros_de_sintomas': [
                {**_fila(r), 'evaluacion': _fila(r.evaluacion) if r.evaluacion else None}
                for r in registros
            ],
            'seguimientos_de_evolucion': [_fila(s) for s in nino.seguimientos],
            'solicitudes_de_atencion': [
                {**_fila(s), 'profesional': s.profesional.nombre_completo if s.profesional else None}
                for s in SolicitudAtencion.query.filter_by(nino_id=nino.id).order_by(SolicitudAtencion.id).all()
            ],
            'profesionales_autorizados': [
                {**_fila(a), 'profesional': a.profesional.nombre_completo} for a in nino.autorizaciones
            ],
            'mensajes': [
                {'fecha': _serializar(m.fecha), 'autor': m.nombre_autor(), 'contenido': m.contenido,
                 'adjuntos': [{'tipo': a.tipo, 'nombre': a.nombre_original, 'tamano_bytes': a.tamano}
                              for a in m.adjuntos]}
                for m in Mensaje.query.filter_by(nino_id=nino.id).order_by(Mensaje.fecha).all()
            ],
            'indicaciones_de_medicamentos': [
                {**_fila(receta), 'medicamentos': [
                    {**_fila(med), 'tomas': [_fila(t) for t in med.tomas]} for med in receta.medicamentos
                ]}
                for receta in nino.recetas
            ],
        })

    solicitudes = SolicitudDerechos.query.filter_by(usuario_id=cuidador.id, usuario_tipo='cuidador').all()
    return {
        'generado_en': _serializar(datetime.now()),
        'responsable_del_tratamiento': current_app.config['RESPONSABLE_NOMBRE'],
        'version_politica_vigente': current_app.config['POLITICA_VERSION'],
        'cuenta': _fila(cuidador),
        'consentimientos': [_fila(c) for c in historial_consentimientos(cuidador)],
        'solicitudes_de_derechos': [_fila(s) for s in solicitudes],
        'consultas_al_asistente': [
            _fila(c) for c in ConsultaIA.query.filter_by(cuidador_id=cuidador.id).order_by(ConsultaIA.id).all()
        ],
        'ninos': ninos,
    }


def exportar_datos_profesional(profesional):
    return {
        'generado_en': _serializar(datetime.now()),
        'responsable_del_tratamiento': current_app.config['RESPONSABLE_NOMBRE'],
        'version_politica_vigente': current_app.config['POLITICA_VERSION'],
        'cuenta': _fila(profesional),
        'consentimientos': [_fila(c) for c in historial_consentimientos(profesional)],
        'pacientes_autorizados': [
            {'nino_id': a.nino_id, 'activa': a.activa, 'fecha_autorizacion': _serializar(a.fecha_autorizacion)}
            for a in profesional.autorizaciones
        ],
    }

