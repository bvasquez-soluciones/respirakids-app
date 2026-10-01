"""Plazos legales para atender solicitudes de los titulares (Ley 1581 de 2012, arts. 14 y 15).

Los días hábiles se cuentan de lunes a viernes. Los festivos de Colombia NO se descuentan: el plazo
calculado puede ser más corto que el legal, nunca más largo (criterio conservador).
"""
from datetime import timedelta

from app.fechas import a_local

DIAS_HABILES = {'consulta': 10}     # consultas
DIAS_HABILES_RECLAMO = 15           # rectificación, supresión, revocatoria y quejas


def sumar_dias_habiles(inicio, dias):
    fecha = inicio
    while dias > 0:
        fecha += timedelta(days=1)
        if fecha.weekday() < 5:
            dias -= 1
    return fecha


def fecha_limite(solicitud):
    """Fecha (local) en que vence el plazo para responder la solicitud."""
    dias = DIAS_HABILES.get(solicitud.tipo, DIAS_HABILES_RECLAMO)
    return sumar_dias_habiles(a_local(solicitud.fecha_solicitud).date(), dias)


def dias_restantes(solicitud, hoy):
    return (fecha_limite(solicitud) - hoy).days
