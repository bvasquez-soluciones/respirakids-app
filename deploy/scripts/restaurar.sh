#!/usr/bin/env bash
# Restaura un respaldo de la base de datos de RespiraKids.
#
#   restaurar.sh ARCHIVO.dump[.gpg] BASE_DESTINO
#
# Por seguridad, la restauración se hace en una base de datos NUEVA y vacía (p. ej. respirakids_verificacion).
# Úsalo cada mes para comprobar que los respaldos realmente se pueden restaurar. Reemplazar la base de producción
# es un paso manual y deliberado (detener el servicio, renombrar bases), descrito en docs/DESPLIEGUE.md.
set -euo pipefail

ARCHIVO="${1:?Uso: restaurar.sh ARCHIVO.dump[.gpg] BASE_DESTINO}"
DESTINO="${2:?Indica el nombre de la base de datos destino (nueva)}"

if [ "$DESTINO" = "respirakids_db" ] || [ "$DESTINO" = "${BASE_PRODUCCION:-respirakids_db}" ]; then
  echo "Por seguridad, este script no restaura sobre la base de producción. Usa una base nueva." >&2
  exit 1
fi

TEMPORAL=""
if [[ "$ARCHIVO" == *.gpg ]]; then
  TEMPORAL="$(mktemp)"
  trap 'shred -u "$TEMPORAL" 2>/dev/null || rm -f "$TEMPORAL"' EXIT
  gpg --batch --yes --decrypt --output "$TEMPORAL" "$ARCHIVO"
  ARCHIVO="$TEMPORAL"
fi

createdb "$DESTINO"
pg_restore --no-owner --no-privileges --exit-on-error --dbname="$DESTINO" "$ARCHIVO"

echo "Restaurado en $DESTINO. Verificación rápida:"
psql --dbname="$DESTINO" --tuples-only --command \
  "SELECT 'alembic: ' || version_num FROM alembic_version
   UNION ALL SELECT 'niños: ' || count(*) FROM ninos
   UNION ALL SELECT 'evaluaciones: ' || count(*) FROM evaluaciones;"
