# Seguridad, cuentas y protección de datos

Inventario de los mecanismos de un sistema real de salud en RespiraKids: qué existía, qué se agregó en la
Fase 10 y qué queda recomendado antes de comercializar. Cada punto indica dónde está implementado y cómo se prueba.

## 1. Estado general

| Área | Estado | Implementación | Pruebas |
|---|---|---|---|
| Registro con aceptación de la política (Ley 1581) | Existía | `auth.registro`, `services/consentimiento.py` | `test_auth`, `test_privacidad` |
| Contraseñas con hash (Werkzeug, scrypt/pbkdf2) | Existía | `UsuarioMixin.set_password` | `test_auth` |
| Política de contraseña (8+ caracteres, letras y números) | Existía | `forms.password_segura` | `test_formularios` |
| Bloqueo tras 5 intentos fallidos (15 min) | Existía | `auth._registrar_intento_fallido` | `test_auth` |
| Mensaje genérico ante credenciales incorrectas | Existía | `MENSAJE_CREDENCIALES` | `test_auth` |
| Límite de peticiones (login, registro, asistente) | Existía | Flask-Limiter (Redis en producción) | `test_produccion` |
| Regeneración de sesión al iniciar sesión (fijación) | Existía | `session.clear()` antes de `login_user` | `test_auth` |
| Cookies seguras (`HttpOnly`, `Secure`, `SameSite`, `__Host-`) | Existía | `config.py` | `test_produccion` |
| CSRF en todos los formularios | Existía | Flask-WTF `CSRFProtect` | — |
| Redirecciones abiertas bloqueadas (`next`) | Existía | `auth._siguiente_seguro` | `test_auth` |
| Roles (cuidador, profesional, admin) y acceso por niño (404 ante ids ajenos) | Existía | `decorators.rol_requerido`, `services/acceso.py` | `test_acceso` |
| Aprobación de profesionales y contraseña temporal obligatoria | Existía | `admin`, `auth.exigir_cambio_de_password_temporal` | `test_admin` |
| Cambio de contraseña verificando la actual | Existía | `dashboard._procesar_cambio_password` | `test_admin` |
| Consentimiento por niño, derechos del titular, exportación | Existía | `privacidad`, `services/datos_titular.py` | `test_privacidad` |
| Auditoría de seguridad y de acceso a datos de niños | Existía | `services/auditoria.py` (`logs_seguridad`, `logs_actividad`) | varios |
| Cabeceras de seguridad, HSTS, HTTPS obligatorio | Existía | Flask-Talisman + Nginx | `test_produccion`, CI |
| Páginas de error sin detalles internos, id de petición en logs | Existía | `app/__init__.py`, `sistema.py` | `test_aplicacion` |
| **Recuperación de contraseña por correo** | **Agregado** | `auth.recuperar`, `auth.restablecer`, `services/cuentas.py` | `test_cuentas` |
| **Verificación de correo del cuidador** | **Agregado** | `auth.verificar_correo`, `auth.reenviar_verificacion` | `test_cuentas` |
| **Cierre de las demás sesiones al cambiar o restablecer la contraseña** | **Agregado** | `UsuarioMixin.huella_sesion`, `load_user` | `test_cuentas` |
| **Cierre de sesión solo por POST** (anti-CSRF de logout) | **Agregado** | `auth.logout` | `test_cuentas` |
| **Correo saliente obligatorio en producción** | **Agregado** | `ProductionConfig.validar`, `services/correo.py` | `test_produccion` |
| **CSP sin `'unsafe-inline'`** | **Agregado** (diseño) | `app/__init__.py`, JS en `static/js` | `test_diseno` |
| **Política de datos v2.0** (no venta, IA/ML, Decreto 1377, conservación, sin garantía absoluta) | **Agregado** | `templates/privacidad/_contenido_politica.html` | `test_privacidad` |
| **Términos y condiciones de uso** con aceptación versionada | **Agregado** | `/privacidad/terminos`, `services/consentimiento.py` | `test_privacidad` |
| **Supresión por anonimización** (ejecutable por el administrador) | **Agregado** | `services/supresion.py`, `admin.ejecutar_supresion` | `test_supresion` |
| **Período de conservación** (2 años de inactividad) | **Agregado** | `flask privacidad conservacion` | `test_supresion` |

## 2. Qué se agregó y cómo funciona

### 2.1 Recuperación de contraseña
1. "¿Olvidaste tu contraseña?" (pantalla de inicio de sesión) → `/auth/recuperar`.
2. Se responde **siempre el mismo mensaje**, exista o no la cuenta (no se pueden descubrir correos registrados).
3. Si la cuenta existe (y, si es profesional, está aprobada) se envía un enlace con un token aleatorio de 256 bits.
   En la base de datos solo se guarda su **hash SHA-256** y su vencimiento (**60 minutos**,
   `MINUTOS_ENLACE_RECUPERACION`). Pedir otro enlace invalida el anterior.
4. `/auth/restablecer/<token>`: exige la misma política de contraseña. Al guardar:
   el token se borra (un solo uso), la cuenta se desbloquea, se elimina una contraseña temporal pendiente,
   el correo del cuidador queda verificado y **se cierran todas las sesiones abiertas**.
5. Límites: 5 solicitudes por minuto y 20 por hora por IP; eventos de auditoría `recuperacion_solicitada`,
   `password_restablecida`, `recuperacion_enlace_invalido`.

Las columnas `token_recuperacion` y `token_recuperacion_expira` ya existían en la base de datos (provenían de la
versión anterior del sistema); no fue necesaria ninguna migración.

### 2.2 Verificación de correo (cuidadores)
- Al registrarse se envía un enlace de confirmación (vigencia **48 horas**, `HORAS_ENLACE_VERIFICACION`).
- **No bloquea el uso**: un cuidador no debe quedar sin acceso a la información de su hijo/a por un correo
  demorado. Mientras no confirme, el inicio muestra un aviso con el botón "Reenviar enlace" (3 por minuto, 10 por día).
- Importa porque el correo es el único canal para recuperar la cuenta.
- Los profesionales no la necesitan: su cuenta la crea o aprueba un administrador.

### 2.3 Sesiones ligadas a la contraseña
El identificador de sesión es `<tipo>-<id>-<huella>`, donde la huella es un resumen de 16 caracteres del hash de la
contraseña. Si la contraseña cambia (desde el perfil o por recuperación), la huella deja de coincidir y **toda sesión
abierta en otro dispositivo se cierra** en su siguiente petición. Quien hace el cambio conserva su sesión.
Al desplegar esta versión, las sesiones existentes se cierran una vez (formato anterior): es esperado.

### 2.4 Cierre de sesión
Solo una petición **POST con token CSRF** cierra la sesión. Una visita GET a `/auth/logout` muestra una confirmación;
así un enlace o imagen de otro sitio no puede cerrar la sesión de un usuario.

### 2.5 Correo saliente
`services/correo.py` (Flask-Mail). Cada mensaje tiene versión de texto y HTML (`templates/correo/`).
En producción `MAIL_SERVER` y `MAIL_DEFAULT_SENDER` son obligatorios; en desarrollo, sin servidor configurado, el
correo se escribe en el log. Un fallo de envío nunca se muestra al usuario ni revela si la cuenta existe; el log no
registra destinatarios ni enlaces.

## 3. Seguimiento de evolución (cuidador)
Tabla nueva `seguimientos_evolucion` (migración `ae1e8f667adf`, solo crea la tabla).
El cuidador indica desde la tarjeta de cada niño/a si **mejoró, sigue igual o empeoró** desde la última evaluación.
- Es su percepción: **no** pasa por el motor clínico ni cambia la clasificación AIEPI.
- Si indica que empeoró, se le sugiere registrar los síntomas de nuevo (el motor existente da la orientación) y
  consultar ante signos de alarma.
- Una evaluación nueva reinicia la pregunta. El profesional autorizado ve la última respuesta en el detalle del
  paciente. Se incluye en la exportación de datos del titular. Acceso solo del cuidador del niño/a (404 a otros),
  exige el consentimiento de datos de salud y queda en la auditoría (`registrar_seguimiento`).
- Pruebas: `tests/test_seguimiento.py`.

## 4. Política, términos, supresión y conservación

### 4.1 Política de tratamiento de datos (versión 2.0)
Agrega: marco normativo (Constitución art. 15, Ley 1581 de 2012, Decreto 1377 de 2013 compilado en el Decreto 1074
de 2015, art. 7 sobre niños y niñas); declaración expresa de que **los datos no se venden, alquilan ni comercializan**;
sección de IA y ML (qué se envía al proveedor, qué se guarda, qué no hace; el modelo ML se entrena solo con datos
sintéticos); supresión por anonimización; período de conservación; seguridad como "medidas técnicas, humanas y
administrativas razonables" — **sin prometer seguridad absoluta** — y aviso de incidentes a la SIC.
Al subir `POLITICA_VERSION` a 2.0, todos los usuarios la aceptan de nuevo en su siguiente ingreso.

### 4.2 Términos y condiciones de uso (versión 1.0)
`/privacidad/terminos`. Se aceptan en una casilla **separada** de la política (la autorización de datos sensibles
debe ser expresa e independiente). Cada aceptación queda en `consentimientos` (tipo `terminos_uso`) con su versión;
cambiar `TERMINOS_VERSION` vuelve a pedirla.

### 4.3 Supresión de datos
Cuando un titular radica una solicitud de **supresión** desde "Mis datos", el administrador la revisa en
*Administración → Solicitudes* y, si procede, pulsa **Anonimizar datos** escribiendo `ANONIMIZAR`.
- Si la solicitud se refiere a un niño/a: se anonimiza solo ese niño/a. Si no: la cuenta completa (y sus niños/as).
- **Se elimina:** mensajes, consultas al asistente, notificaciones y copias versionadas de indicaciones.
- **Se anonimiza:** nombres, documentos, correo, teléfono, foto, notas y observaciones; la fecha de nacimiento se
  reduce al día 1 del mes; los niños quedan **desvinculados** del cuidador.
- **Se conserva sin identificar:** síntomas, evaluaciones, seguimientos y medicamentos (estadística); y como prueba
  legal, los consentimientos, la solicitud y los registros de seguridad.
- La cuenta queda inutilizable (correo `@anonimizado.invalid`, contraseña aleatoria), la solicitud pasa a
  *resuelta* y el titular recibe la constancia en su correo original. Queda en la auditoría (`supresion_ejecutada`).
- Una cuenta de administrador no se anonimiza (primero se le quita el rol).

### 4.4 Período de conservación
Política: mientras la cuenta esté activa y hasta **2 años** después de la última actividad
(`CONSERVACION_ANIOS_INACTIVIDAD`). `flask privacidad conservacion` lista las cuentas vencidas sin modificarlas;
con `--ejecutar` las anonimiza igual que una supresión. Programarlo mensualmente (ver `docs/DESPLIEGUE.md`).

## 5. Atención por mensajes y acceso de los profesionales de la clínica

**Quién ve qué** (política 2.1, consentimiento por niño/a actualizado):
| Información | Quién la ve |
|---|---|
| Semáforo: nombre, edad, nivel y señales de la última evaluación, evolución reportada | Todos los profesionales de la clínica (`/dashboard/semaforo`), para priorizar la atención |
| Expediente completo: historial, evaluaciones, ficha, condiciones de base, medicamentos | Solo los profesionales que el cuidador autorice |
| Conversaciones | Solo el cuidador y ese profesional (una conversación privada por profesional) |

**Flujo** (`services/atencion.py`, pruebas en `tests/test_atencion.py`):
1. El cuidador pulsa "Conectar con un profesional" y escribe el motivo → "Conectando con un profesional de salud…".
   Si la última evaluación es roja, se le indica acudir a urgencias de inmediato y no esperar la respuesta.
2. Reciben el aviso los profesionales **disponibles** con **cupo** (`CUPO_CASOS_POR_PROFESIONAL = 15` casos abiertos).
3. El primero que pulsa "Atender" toma el caso (asignación atómica: nunca dos profesionales para el mismo caso);
   el motivo abre su conversación privada.
4. El cuidador ve "Conectado" y responde si **autoriza** a ese profesional el expediente completo (crea la
   autorización) o prefiere **solo conversar**.
5. El profesional **cierra el caso** (libera cupo); la conversación queda disponible para volver a comunicarse.
   Cada profesional puede pausar las nuevas solicitudes ("No disponible").

No hay llamadas ni videollamadas: la atención es por mensajes y no es un canal de urgencias.
La supresión anonimiza también el motivo de las solicitudes; "Mis datos" las incluye.

### 5.1 Videollamadas (telemedicina)
- Solo el **profesional que atiende un caso abierto** puede iniciarla (`/videollamada/caso/<id>/iniciar`); solo sus
  dos participantes pueden ver la sala, consultar su estado o enviar señales (cualquier otra persona recibe 404).
- El cuidador debe **aceptar la atención por videollamada** para contestar; se guarda la fecha del consentimiento
  (`videollamadas.consentimiento_fecha`) y queda en la auditoría.
- El video y el audio viajan **directamente y cifrados entre los dos navegadores** (WebRTC, DTLS-SRTP). Si la red no
  lo permite, pasan por un servidor TURN propio, que no puede descifrarlos. **No se graba nada.**
- El servidor solo intercambia los mensajes técnicos de conexión (`senales_videollamada`, incluyen direcciones de
  red) y **los borra al terminar** la llamada. Se guarda: fecha, duración, estado y consentimiento. En la
  conversación queda una constancia con la duración.
- Termina sola si nadie contesta en 60 s (perdida), si un lado deja de responder 45 s o si se cierra el caso.
- Credenciales TURN temporales (3 h) firmadas con `TURN_SECRETO`, que nunca llega al navegador.
- `Permissions-Policy: camera=(self), microphone=(self)`: ningún contenido de terceros puede pedir la cámara.
- La supresión de datos desvincula las llamadas del cuidador y borra sus señales.
- La política de datos (v2.2) y los términos (v1.1) informan las videollamadas: no se graban, qué se registra,
  cifrado y quién participa. Al subir la versión, cada usuario debe aceptarlas de nuevo al ingresar.
- Pendiente legal: confirmar la habilitación de la clínica en telemedicina (Resolución 2654 de 2019) y que el
  abogado revise estos textos.
- Pruebas: `tests/test_videollamadas.py`.

## 6. Recomendado antes de comercializar (no implementado)
Se dejan documentados para decidir con el equipo; ninguno es necesario para operar un piloto controlado.

| Recomendación | Motivo |
|---|---|
| Segundo factor (TOTP) para administradores y profesionales | Acceden a datos de varios menores; es el control más eficaz contra robo de contraseñas. |
| Rechazar contraseñas filtradas (k-anonimato de *Have I Been Pwned*) | Recomendación NIST 800-63B. Implica consultar un servicio externo. |
| Tiempo de inactividad más corto para profesionales (p. ej. 30 min) | Hoy la sesión vence tras 8 h sin actividad para todos los roles. |
| Aviso por correo de inicio de sesión desde un dispositivo nuevo | Detección temprana de accesos indebidos. |
| Pruebas de penetración externas | Requisito habitual de clientes del sector salud. |
| **Revisión jurídica** de la política, los términos y el plazo de conservación | Los textos son borradores técnicos. En especial, definir si los registros se consideran historia clínica (conservación de 15 años, Resolución 839 de 2017). |
