"""Indicaciones de medicamentos registradas por profesionales y administración por el cuidador.

RespiraKids no recomienda ni calcula medicamentos o dosis: solo registra lo que indica un profesional
autorizado, programa los recordatorios según la frecuencia indicada y permite al cuidador marcar las tomas.
"""
import json
from datetime import timedelta

from app import db
from app.fechas import fecha_hora
from app.models import MedicamentoRecetado, Receta, TomaMedicamento, VersionRegistro, ahora_utc
from app.services.notificaciones import notificar

MAX_TOMAS_PROGRAMADAS = 200


def versionar(tabla, registro_id, datos, accion, usuario):
    """Guarda una versión inmutable del registro (trazabilidad de cambios clínicos)."""
    version = (VersionRegistro.query.filter_by(tabla=tabla, registro_id=registro_id).count()) + 1
    db.session.add(VersionRegistro(
        tabla=tabla, registro_id=registro_id, version=version, accion=accion,
        datos=json.dumps(datos, ensure_ascii=False, default=str),
        usuario_id=usuario.id, usuario_tipo=usuario.tipo_usuario,
    ))


def _datos_receta(receta):
    return {
        'nino_id': receta.nino_id, 'profesional_id': receta.profesional_id, 'motivo': receta.motivo,
        'indicaciones_generales': receta.indicaciones_generales, 'activa': receta.activa,
        'medicamentos': [{
            'nombre': m.nombre, 'dosis': m.dosis, 'frecuencia_horas': m.frecuencia_horas,
            'duracion_dias': m.duracion_dias, 'instrucciones': m.instrucciones,
            'fecha_inicio': m.fecha_inicio, 'activo': m.activo,
        } for m in receta.medicamentos],
    }


def programar_tomas(medicamento):
    """Crea las tomas programadas desde la fecha de inicio, cada `frecuencia_horas`, durante `duracion_dias`.

    Sin duración indicada no se programan tomas (el cuidador ve la indicación pero no recordatorios).
    """
    if not medicamento.duracion_dias:
        return 0
    total = min((medicamento.duracion_dias * 24) // medicamento.frecuencia_horas, MAX_TOMAS_PROGRAMADAS)
    for k in range(total):
        db.session.add(TomaMedicamento(
            medicamento_id=medicamento.id,
            hora_programada=medicamento.fecha_inicio + timedelta(hours=k * medicamento.frecuencia_horas),
            administrada=False,
        ))
    return total


def crear_receta(nino, profesional, motivo, indicaciones, fecha_inicio_utc, medicamentos):
    """Crea la receta, sus medicamentos y las tomas programadas, y notifica al cuidador."""
    receta = Receta(nino_id=nino.id, profesional_id=profesional.id, motivo=motivo,
                    indicaciones_generales=indicaciones, activa=True)
    db.session.add(receta)
    db.session.flush()
    for datos in medicamentos:
        medicamento = MedicamentoRecetado(receta_id=receta.id, fecha_inicio=fecha_inicio_utc, activo=True, **datos)
        db.session.add(medicamento)
        db.session.flush()
        programar_tomas(medicamento)

    db.session.flush()
    versionar('recetas', receta.id, _datos_receta(receta), 'crear', profesional)
    notificar(nino.cuidador_id, 'cuidador', 'nueva_receta', 'Nueva indicación de medicamentos',
              f'{profesional.nombre_completo} registró una indicación para {nino.nombre}.', 'medicamentos', nino.id)
    db.session.commit()
    return receta


def suspender_receta(receta, profesional):
    receta.activa = False
    for medicamento in receta.medicamentos:
        medicamento.activo = False
    versionar('recetas', receta.id, _datos_receta(receta), 'suspender', profesional)
    notificar(receta.nino.cuidador_id, 'cuidador', 'receta_suspendida', 'Indicación de medicamentos suspendida',
              f'{profesional.nombre_completo} suspendió la indicación del {fecha_hora(receta.fecha)} '
              f'para {receta.nino.nombre}.', 'medicamentos', receta.nino_id)
    db.session.commit()


def marcar_toma(toma, cuidador, administrada=True):
    toma.administrada = administrada
    toma.hora_administrada = ahora_utc() if administrada else None
    toma.administrado_por_id = cuidador.id if administrada else None
    db.session.commit()


def recetas_del_nino(nino, solo_activas=False):
    consulta = Receta.query.filter_by(nino_id=nino.id)
    if solo_activas:
        consulta = consulta.filter(Receta.activa.is_(True))
    return consulta.order_by(Receta.fecha.desc()).all()


def tomas_pendientes(nino, horas=24):
    """Tomas no administradas de medicamentos activos: vencidas en las últimas `horas` y próximas `horas`."""
    ahora = ahora_utc()
    return (
        TomaMedicamento.query
        .join(MedicamentoRecetado, MedicamentoRecetado.id == TomaMedicamento.medicamento_id)
        .join(Receta, Receta.id == MedicamentoRecetado.receta_id)
        .filter(
            Receta.nino_id == nino.id, Receta.activa.is_(True), MedicamentoRecetado.activo.is_(True),
            TomaMedicamento.administrada.isnot(True),
            TomaMedicamento.hora_programada.between(ahora - timedelta(hours=horas), ahora + timedelta(hours=horas)),
        )
        .order_by(TomaMedicamento.hora_programada)
        .all()
    )


def cumplimiento(medicamento):
    """Tomas administradas sobre tomas cuya hora ya pasó (None si aún no hay tomas vencidas)."""
    vencidas = [t for t in medicamento.tomas if t.hora_programada <= ahora_utc()]
    if not vencidas:
        return None
    administradas = sum(1 for t in vencidas if t.administrada)
    return {'administradas': administradas, 'vencidas': len(vencidas),
            'porcentaje': round(100 * administradas / len(vencidas))}
