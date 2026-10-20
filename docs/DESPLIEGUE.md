# Despliegue de RespiraKids en producción

Guía para instalar RespiraKids en un servidor Linux propio (VPS). Los archivos mencionados están en `deploy/`.

## 1. Arquitectura

```
Internet ──HTTPS──> Nginx (443) ──HTTP local──> Gunicorn (127.0.0.1:8000) ──> Flask (RespiraKids)
                     │  TLS, HSTS, límite de peticiones,             │
                     │  archivos estáticos                           ├──> PostgreSQL (datos)
                     └─ página de mantenimiento                      ├──> Redis (límite de peticiones)
                                                                     └──> Google Gemini (asistente, opcional)
```

| Entorno | `RESPIRAKIDS_ENV` | Base de datos | Uso |
|---|---|---|---|
| Desarrollo | `development` | PostgreSQL local | Programar en el equipo |
| Pruebas | `testing` | SQLite en memoria (y PostgreSQL en CI) | `pytest` y GitHub Actions |
| Producción | `production` | PostgreSQL del servidor | Usuarios reales |

## 2. Requisitos del servidor

- Ubuntu Server 24.04 LTS (o similar), mínimo 2 vCPU, 4 GB de RAM, 40 GB de disco.
- Python 3.14 (el proyecto se prueba con 3.14; instalable con `uv python install 3.14` o pyenv).
- PostgreSQL 16 o superior, Redis 7 o superior, Nginx, certbot, git.
- Un dominio apuntando a la IP del servidor.

## 3. Instalación

### 3.1 Usuario y carpetas
```bash
sudo adduser --system --group --home /srv/respirakids respirakids
sudo mkdir -p /etc/respirakids /var/backups/respirakids /var/log/respirakids
sudo chown respirakids:respirakids /var/backups/respirakids /var/log/respirakids
sudo -u respirakids git clone https://github.com/bvasquez-soluciones/respirakids-app.git /srv/respirakids
```

### 3.2 Base de datos (usuario con permisos mínimos)
```bash
sudo -u postgres psql -c "CREATE ROLE respirakids LOGIN PASSWORD 'CAMBIAR-POR-UNA-CLAVE-LARGA';"
sudo -u postgres psql -c "CREATE DATABASE respirakids_db OWNER respirakids;"
```
La base de datos no debe aceptar conexiones desde fuera del servidor (`listen_addresses = 'localhost'`).

### 3.3 Redis
En `/etc/redis/redis.conf`: `bind 127.0.0.1 ::1` y `protected-mode yes`. Luego `sudo systemctl enable --now redis-server`.

### 3.4 Entorno de Python
```bash
cd /srv/respirakids
sudo -u respirakids python3.14 -m venv venv
sudo -u respirakids venv/bin/pip install -r requirements.txt
```

### 3.5 Variables de entorno
Crear `/etc/respirakids/respirakids.env` (propietario `respirakids`, permisos `600`) a partir de `.env.example`:

```ini
RESPIRAKIDS_ENV=production
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=postgresql://respirakids:CLAVE@localhost:5432/respirakids_db
RATELIMIT_STORAGE_URI=redis://localhost:6379/0
# Obligatoria: sin ella el servidor no arranca (el asistente necesita la IA para redactar sus respuestas).
GEMINI_API_KEY=<clave del proveedor de IA>
# Correo saliente (recuperación de contraseña y verificación de correo). Usar un proveedor transaccional
# (SES, Mailgun, SendGrid, Postmark...) con SPF, DKIM y DMARC configurados en el dominio.
MAIL_SERVER=smtp.proveedor.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=...
MAIL_PASSWORD=...
# Entre comillas: los signos < > rompen el archivo cuando lo leen los scripts (respaldos, cron).
MAIL_DEFAULT_SENDER="RespiraKids <no-responder@TU-DOMINIO>"
ML_HABILITADO=false
RESPONSABLE_NOMBRE=...
RESPONSABLE_ID=...
RESPONSABLE_DIRECCION=...
RESPONSABLE_CORREO=...
RESPONSABLE_TELEFONO=...
# Solo después de la firma del profesional de salud (docs/REGLAS_CLINICAS_v1.md):
REGLAS_CLINICAS_VALIDADAS=v1-aiepi
```

La aplicación **se niega a arrancar en producción** si falta `SECRET_KEY` (o tiene menos de 32 caracteres), si
`DATABASE_URL` no está definida, si no hay correo saliente (`MAIL_SERVER`, `MAIL_DEFAULT_SENDER`), si el límite de
peticiones no usa Redis o si las reglas clínicas no están validadas.

### 3.6 Esquema, administrador y base de conocimiento
```bash
cd /srv/respirakids
sudo -u respirakids bash -c 'set -a; . /etc/respirakids/respirakids.env; set +a; export FLASK_APP=wsgi.py
  venv/bin/flask db upgrade
  venv/bin/flask admin crear
  venv/bin/flask conocimiento importar'
```

### 3.7 Servicio (systemd + Gunicorn)
```bash
sudo cp deploy/systemd/respirakids.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now respirakids
curl -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/salud   # {"base_de_datos":"ok","estado":"ok"}
```

### 3.8 Nginx y HTTPS
```bash
sudo cp deploy/nginx/respirakids-proxy.conf /etc/nginx/snippets/
sudo cp deploy/nginx/respirakids.conf /etc/nginx/sites-available/   # cambiar el dominio dentro del archivo
sudo ln -s /etc/nginx/sites-available/respirakids.conf /etc/nginx/sites-enabled/
sudo certbot certonly --webroot -w /var/www/certbot -d TU-DOMINIO
sudo nginx -t && sudo systemctl reload nginx
```

### 3.9 Cortafuegos
```bash
sudo ufw allow OpenSSH && sudo ufw allow 'Nginx Full' && sudo ufw enable
```
PostgreSQL, Redis y Gunicorn solo escuchan en `localhost`.

### 3.10 Servidor TURN para las videollamadas (coturn)
El video viaja directo y cifrado entre los dos navegadores (WebRTC). Cuando la red no lo permite (datos móviles,
redes corporativas), pasa por un servidor TURN propio, que solo reenvía el tráfico cifrado: no puede ver ni grabar
la llamada.

```bash
sudo apt install coturn
```
`/etc/turnserver.conf` (mínimo):
```ini
listening-port=3478
tls-listening-port=5349
fingerprint
use-auth-secret
static-auth-secret=<cadena larga y aleatoria: python -c "import secrets; print(secrets.token_hex(32))">
realm=respirakids.ejemplo.co
cert=/etc/letsencrypt/live/respirakids.ejemplo.co/fullchain.pem
pkey=/etc/letsencrypt/live/respirakids.ejemplo.co/privkey.pem
no-cli
no-multicast-peers
denied-peer-ip=10.0.0.0-10.255.255.255
denied-peer-ip=172.16.0.0-172.31.255.255
denied-peer-ip=192.168.0.0-192.168.255.255
```
Cortafuegos: `sudo ufw allow 3478,5349/tcp && sudo ufw allow 3478,5349/udp && sudo ufw allow 49152:65535/udp`.
En `respirakids.env`:
```ini
WEBRTC_STUN_URLS=stun:respirakids.ejemplo.co:3478
TURN_URLS=turn:respirakids.ejemplo.co:3478?transport=udp,turns:respirakids.ejemplo.co:5349?transport=tcp
TURN_SECRETO=<el mismo static-auth-secret>
```
RespiraKids entrega a cada participante credenciales TURN temporales (3 horas) firmadas con ese secreto; el secreto
nunca llega al navegador. `/admin/configuracion` muestra si el TURN está configurado.

## 4. Respaldos

- `deploy/scripts/respaldo.sh` respalda la base de datos (formato `pg_dump` custom, verificado tras crearlo), las
  fotos de perfil y los **adjuntos de los mensajes** (`datos/adjuntos`: fotos, PDF y notas de voz), genera sumas
  SHA-256 y borra los respaldos más antiguos que `DIAS_RETENCION`.
- La carpeta de adjuntos es privada: `sudo -u respirakids mkdir -p /srv/respirakids/datos/adjuntos && chmod 700
  /srv/respirakids/datos /srv/respirakids/datos/adjuntos`. Nginx **no** debe servirla (la aplicación la entrega
  solo a quien puede ver cada conversación). Se puede ubicar en otro disco con `ADJUNTOS_FOLDER`.
- **Cifrado recomendado:** defina `GPG_DESTINATARIO` en `/etc/respirakids/respaldo.env`. Son datos de salud de menores.
- Programarlo a diario (cron del usuario `respirakids`):
  ```
  30 2 * * * /srv/respirakids/deploy/scripts/respaldo.sh >> /var/log/respirakids/respaldo.log 2>&1
  ```
- **Copia externa:** sincronizar `/var/backups/respirakids` con un almacenamiento fuera del servidor.
- **Período de conservación** (Ley 1581): revisar cada mes las cuentas sin actividad por más de 2 años y
  anonimizarlas (ver `docs/SEGURIDAD_Y_CUENTAS.md`). Primero sin `--ejecutar` para revisar la lista:
  ```
  0 3 1 * * cd /srv/respirakids && set -a && . /etc/respirakids/respirakids.env && set +a && FLASK_APP=wsgi.py venv/bin/flask privacidad conservacion >> /var/log/respirakids/conservacion.log 2>&1
  ```
- **Prueba de restauración mensual** (en una base nueva, nunca sobre producción):
  ```bash
  deploy/scripts/restaurar.sh /var/backups/respirakids/respirakids_db_FECHA.dump.gpg respirakids_verificacion
  dropdb respirakids_verificacion   # tras comprobar los conteos
  ```

Restaurar sobre producción (solo ante una pérdida real): detener el servicio, restaurar en una base nueva, verificarla,
renombrar las bases y volver a iniciar el servicio. Registrar el incidente.

## 5. Operación

| Tarea | Cómo |
|---|---|
| Actualizar a la última versión | `sudo -u respirakids deploy/scripts/actualizar.sh` (respalda, migra, recarga y verifica) |
| Ver logs de la aplicación | `journalctl -u respirakids -f` (cada línea incluye `req=<id de petición>`) |
| Seguir una petición con error | Buscar su `X-Request-ID` en los logs de Nginx y de la aplicación |
| Monitoreo | Vigilar `https://TU-DOMINIO/salud` con un servicio externo (responde 503 si cae la base de datos) |
| Revertir una versión | `git checkout <versión anterior>`, `flask db downgrade` solo si la migración lo permite, recargar el servicio |
| Renovar certificados | certbot lo hace automáticamente; verificar con `sudo certbot renew --dry-run` |
| Auditoría y solicitudes de datos | Panel de administración (`/admin`) |

## 6. Integración continua

`.github/workflows/ci.yml` se ejecuta en cada push y pull request:
- aplica todas las migraciones sobre PostgreSQL vacío y verifica que no falten migraciones (`flask db check`);
- ejecuta las pruebas automatizadas;
- verifica que `docs/REGLAS_CLINICAS_v1.md` esté sincronizado con el código;
- revisa vulnerabilidades conocidas en las dependencias (`pip-audit`).

Solo se debe desplegar código cuya integración continua esté en verde.

## 7. Lista de verificación antes de operar con usuarios reales

**Técnico**
- [ ] HTTPS activo y `http://` redirige a `https://`.
- [ ] `SECRET_KEY` única y larga; `/etc/respirakids/respirakids.env` con permisos 600.
- [ ] Respaldos diarios cifrados, copia externa y una restauración de prueba realizada.
- [ ] `/salud` monitoreado con alertas.
- [ ] Correo saliente probado: recuperación de contraseña y verificación llegan a la bandeja de entrada (no a spam).
- [ ] Asistente probado con la clave real: responde redactando con citas [1], [2]… (si solo muestra fragmentos textuales, la clave o la cuota del proveedor de IA fallan).
- [ ] Integración continua en verde para la versión desplegada.
- [ ] Administrador creado con contraseña robusta; ninguna cuenta ni dato de prueba en producción.

**Clínico**
- [ ] Un profesional de salud revisó y firmó `docs/REGLAS_CLINICAS_v1.md`, y luego se definió `REGLAS_CLINICAS_VALIDADAS`.
- [ ] Decidido si el modelo ML permanece apagado (recomendado: apagado hasta tener datos reales y validación).
- [ ] Videollamadas: la clínica está habilitada en la modalidad de telemedicina (Resolución 2654 de 2019) y definió
  cómo se registra la atención por video en su historia clínica. Si no, no usar el botón de videollamada.
- [ ] Videollamadas probadas entre dos celulares con datos móviles (requiere el servidor TURN de la sección 3.10).

**Legal y privacidad**
- [ ] Política de tratamiento revisada por un abogado; datos del responsable completos (ver `/admin/configuracion`).
- [ ] Período de conservación revisado por el abogado (hoy: 2 años de inactividad) y tarea mensual de conservación programada.
- [ ] Términos y condiciones de uso revisados por un abogado.
- [ ] Acuerdo de tratamiento de datos con el proveedor de IA (transferencia internacional) y con el proveedor del servidor.
- [ ] Registro de la base de datos ante la SIC si aplica.
- [ ] Evaluación regulatoria como software de uso en salud (INVIMA) antes de comercializar.
- [ ] Procedimiento interno para atender solicitudes de datos dentro de los plazos legales.
