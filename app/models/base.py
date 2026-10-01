"""Utilidades compartidas por los modelos."""
from datetime import datetime, timezone


def ahora_utc():
    """Fecha y hora actual en UTC, sin zona horaria (las columnas son TIMESTAMP sin zona)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
