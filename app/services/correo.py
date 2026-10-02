"""Envío de correos transaccionales (recuperación de contraseña, verificación de correo).

Cada correo tiene versión de texto y HTML: templates/correo/<nombre>.txt y .html.
Sin MAIL_SERVER (solo posible fuera de producción, ver ProductionConfig.validar) el correo no se envía:
se escribe en el log para poder probar los flujos en desarrollo.
"""
from flask import current_app, render_template
from flask_mail import Message

from app import mail


def enviar(destinatario, asunto, plantilla, **contexto):
    """Envía un correo. Devuelve True si se entregó al servidor SMTP. Nunca lanza excepciones al llamador:
    un fallo de correo no debe revelar si la cuenta existe ni romper el flujo del usuario."""
    texto = render_template(f'correo/{plantilla}.txt', **contexto)
    html = render_template(f'correo/{plantilla}.html', **contexto)

    if not current_app.config.get('MAIL_SERVER'):
        current_app.logger.warning('Correo NO enviado (MAIL_SERVER vacío, solo desarrollo). Asunto: %s\n%s',
                                   asunto, texto)
        return False
    try:
        mail.send(Message(subject=asunto, recipients=[destinatario], body=texto, html=html))
        return True
    except Exception:  # SMTP caído, credenciales inválidas, tiempo agotado...
        # No se registra el destinatario (dato personal) ni el contenido (contiene enlaces de un solo uso).
        current_app.logger.exception('Error al enviar el correo "%s"', asunto)
        return False
