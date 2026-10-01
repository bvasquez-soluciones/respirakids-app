#!/usr/bin/env bash
# Actualiza RespiraKids en el servidor a la última versión de la rama principal.
#
#   sudo -u respirakids /srv/respirakids/deploy/scripts/actualizar.sh
#
# Orden: respaldo -> código -> dependencias -> migraciones -> reinicio -> chequeo de salud.
set -euo pipefail

DIR_APP="${DIR_APP:-/srv/respirakids}"
RAMA="${RAMA:-main}"
cd "$DIR_APP"

set -a
# shellcheck source=/dev/null
. /etc/respirakids/respirakids.env
set +a
export RESPIRAKIDS_ENV=production FLASK_APP=wsgi.py

echo "1/6 Respaldo previo"
"$DIR_APP/deploy/scripts/respaldo.sh"

echo "2/6 Código ($RAMA)"
git fetch --quiet origin "$RAMA"
git checkout --quiet "$RAMA"
git pull --ff-only --quiet origin "$RAMA"

echo "3/6 Dependencias"
"$DIR_APP/venv/bin/pip" install --quiet -r requirements.txt

echo "4/6 Migraciones de base de datos"
"$DIR_APP/venv/bin/flask" db upgrade

echo "5/6 Reinicio del servicio"
sudo systemctl reload respirakids   # recarga sin cortar las peticiones en curso

echo "6/6 Chequeo de salud"
for _ in 1 2 3 4 5; do
  # Se indica que la petición llega por HTTPS (como lo hace Nginx); si no, la app responde con una redirección.
  if curl --silent --fail --max-redirs 0 -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/salud | grep -q '"ok"'; then
    echo "RespiraKids responde correctamente."
    exit 0
  fi
  sleep 3
done
echo "ERROR: la aplicación no responde. Revisa: journalctl -u respirakids -n 100" >&2
exit 1
