#!/usr/bin/env bash
# Respaldo de RespiraKids: base de datos PostgreSQL + archivos subidos.
#
# Uso (como usuario respirakids, p. ej. desde cron a las 2:30 a. m.):
#   30 2 * * * /srv/respirakids/deploy/scripts/respaldo.sh >> /var/log/respirakids/respaldo.log 2>&1
#
# Variables (en /etc/respirakids/respaldo.env):
#   DATABASE_URL        cadena de conexión de PostgreSQL (obligatoria)
#   DIR_RESPALDOS       carpeta destino (por defecto /var/backups/respirakids)
#   DIAS_RETENCION      días que se conservan los respaldos (por defecto 30)
#   GPG_DESTINATARIO    si se define, los respaldos se cifran con esa llave pública (recomendado: son datos de salud)
set -euo pipefail

# shellcheck source=/dev/null
[ -f /etc/respirakids/respaldo.env ] && . /etc/respirakids/respaldo.env
: "${DATABASE_URL:?Falta DATABASE_URL}"
DIR_RESPALDOS="${DIR_RESPALDOS:-/var/backups/respirakids}"
DIAS_RETENCION="${DIAS_RETENCION:-30}"
DIR_APP="${DIR_APP:-/srv/respirakids}"
FECHA="$(date -u +%Y%m%dT%H%M%SZ)"

umask 077   # los respaldos solo los puede leer su propietario
mkdir -p "$DIR_RESPALDOS"

cifrar() {   # $1 = archivo; deja el resultado en $1 o $1.gpg
  if [ -n "${GPG_DESTINATARIO:-}" ]; then
    gpg --batch --yes --encrypt --recipient "$GPG_DESTINATARIO" --output "$1.gpg" "$1"
    shred -u "$1" 2>/dev/null || rm -f "$1"
    echo "$1.gpg"
  else
    echo "$1"
  fi
}

echo "[$FECHA] Iniciando respaldo"

# 1. Base de datos en formato custom (comprimido, restaurable con pg_restore).
DUMP="$DIR_RESPALDOS/respirakids_db_$FECHA.dump"
pg_dump --format=custom --no-owner --no-privileges --dbname="$DATABASE_URL" --file="$DUMP"
pg_restore --list "$DUMP" > /dev/null   # verifica que el archivo sea legible
DUMP="$(cifrar "$DUMP")"

# 2. Archivos subidos por los usuarios (fotos de perfil).
UPLOADS="$DIR_RESPALDOS/respirakids_uploads_$FECHA.tar.gz"
tar -czf "$UPLOADS" -C "$DIR_APP/app/static" uploads 2>/dev/null || tar -czf "$UPLOADS" --files-from /dev/null
UPLOADS="$(cifrar "$UPLOADS")"

# 3. Sumas de verificación para detectar respaldos dañados.
( cd "$DIR_RESPALDOS" && sha256sum "$(basename "$DUMP")" "$(basename "$UPLOADS")" > "respirakids_$FECHA.sha256" )

# 4. Retención: se borran solo los respaldos de RespiraKids más antiguos que DIAS_RETENCION.
find "$DIR_RESPALDOS" -maxdepth 1 -type f -name 'respirakids_*' -mtime +"$DIAS_RETENCION" -print -delete

echo "[$FECHA] Respaldo completado: $(basename "$DUMP"), $(basename "$UPLOADS")"
# Recomendado: copiar también $DIR_RESPALDOS a un almacenamiento externo (otro servidor o nube) cifrado.
