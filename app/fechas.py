"""Fechas y horas: se guardan en UTC (sin zona) y se muestran en la hora local de los usuarios.

Toda fecha que se muestre o se reciba de un formulario debe pasar por aquí.
"""
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from flask import current_app, has_app_context

ZONA_POR_DEFECTO = 'America/Bogota'


def zona_local():
    nombre = current_app.config.get('ZONA_HORARIA', ZONA_POR_DEFECTO) if has_app_context() else ZONA_POR_DEFECTO
    return ZoneInfo(nombre)


def a_local(valor):
    """Fecha y hora UTC (sin zona) -> hora local. Las fechas sin hora se devuelven igual."""
    if valor is None or not isinstance(valor, datetime):
        return valor
    return valor.replace(tzinfo=timezone.utc).astimezone(zona_local())


def a_utc(valor_local):
    """Fecha y hora local escrita por el usuario (sin zona) -> UTC sin zona, para guardar."""
    if valor_local is None:
        return None
    return valor_local.replace(tzinfo=zona_local()).astimezone(timezone.utc).replace(tzinfo=None)


def ahora_local():
    return datetime.now(zona_local()).replace(tzinfo=None)


def _formatear(valor, formato):
    if valor is None:
        return '—'
    if isinstance(valor, datetime):
        return a_local(valor).strftime(formato)
    if isinstance(valor, date):
        return valor.strftime(formato)
    return str(valor)


def fecha(valor):
    return _formatear(valor, '%d/%m/%Y')


def fecha_hora(valor):
    return _formatear(valor, '%d/%m/%Y %H:%M')


def fecha_hora_corta(valor):
    return _formatear(valor, '%d/%m %H:%M')


def hora(valor):
    return _formatear(valor, '%H:%M')


def mes_anio(valor):
    return _formatear(valor, '%m/%Y')


def iso_local(valor):
    return a_local(valor).isoformat() if isinstance(valor, datetime) else (valor.isoformat() if valor else '')


FILTROS = {
    'fecha': fecha, 'fecha_hora': fecha_hora, 'fecha_hora_corta': fecha_hora_corta,
    'hora': hora, 'mes_anio': mes_anio, 'iso_local': iso_local,
}
