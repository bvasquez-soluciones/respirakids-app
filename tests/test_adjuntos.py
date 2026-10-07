"""Adjuntos en los mensajes: fotos, PDF y notas de voz, con almacenamiento privado y control de acceso."""
import io
import os

from PIL import Image

from app import db
from app.models import AdjuntoMensaje, Mensaje, SolicitudDerechos
from tests.conftest import autorizar, crear_cuidador, crear_nino, crear_profesional, login

PDF = b'%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF'
NOTA_DE_VOZ = b'\x1aE\xdf\xa3' + b'\x00' * 200  # cabecera WebM (lo que graba Chrome/Android)


def _foto_con_gps():
    """JPEG con metadatos EXIF (como las fotos del celular, que suelen incluir la ubicación)."""
    imagen = Image.new('RGB', (40, 30), (200, 80, 80))
    exif = Image.Exif()
    exif[0x010F] = 'TelefonoDePrueba'  # fabricante
    salida = io.BytesIO()
    imagen.save(salida, 'JPEG', exif=exif.tobytes())
    return salida.getvalue()


def _escenario():
    ana = crear_cuidador('ana@test.com')
    sofia = crear_nino(ana, 'Sofía')
    dra = crear_profesional('dra@test.com')
    autorizar(sofia, dra)
    return ana, sofia, dra


def _enviar(client, sofia, dra, datos, nombre, texto=''):
    return client.post(f'/mensajes/nino/{sofia.id}/profesional/{dra.id}',
                       data={'contenido': texto, 'adjunto': (io.BytesIO(datos), nombre)},
                       content_type='multipart/form-data')


def test_foto_se_guarda_privada_y_sin_metadatos(client, app):
    _, sofia, dra = _escenario()
    login(client, 'ana@test.com')
    foto = _foto_con_gps()
    assert b'TelefonoDePrueba' in foto
    _enviar(client, sofia, dra, foto, 'erupcion.jpg', 'Así se ve la piel hoy')
    adjunto = AdjuntoMensaje.query.one()
    assert adjunto.tipo == 'imagen' and adjunto.mensaje.contenido == 'Así se ve la piel hoy'
    ruta = os.path.join(app.config['ADJUNTOS_FOLDER'], adjunto.archivo)
    # Fuera de /static, con nombre aleatorio y sin los metadatos originales.
    assert 'static' not in ruta and adjunto.archivo != 'erupcion.jpg'
    with open(ruta, 'rb') as archivo:
        assert b'TelefonoDePrueba' not in archivo.read()
    respuesta = client.get(f'/mensajes/adjunto/{adjunto.id}')
    assert respuesta.status_code == 200 and respuesta.mimetype == 'image/jpeg'
    assert 'no-store' in respuesta.headers['Cache-Control']


def test_pdf_y_nota_de_voz_sin_texto(client, app):
    _, sofia, dra = _escenario()
    login(client, 'ana@test.com')
    _enviar(client, sofia, dra, PDF, 'examen.pdf')
    _enviar(client, sofia, dra, NOTA_DE_VOZ, 'nota-de-voz.webm')
    tipos = [a.tipo for a in AdjuntoMensaje.query.order_by(AdjuntoMensaje.id)]
    assert tipos == ['documento', 'audio']
    pdf = AdjuntoMensaje.query.filter_by(tipo='documento').one()
    assert 'attachment' in client.get(f'/mensajes/adjunto/{pdf.id}').headers['Content-Disposition']
    # Aparecen en la actualización sin recargar.
    nuevos = client.get(f'/mensajes/nino/{sofia.id}/profesional/{dra.id}/nuevos?desde=0').get_json()['mensajes']
    assert [m['adjuntos'][0]['tipo'] for m in nuevos] == ['documento', 'audio']


def test_rechaza_archivos_no_permitidos(client, app):
    _, sofia, dra = _escenario()
    login(client, 'ana@test.com')
    # Un ejecutable renombrado como imagen se rechaza por su contenido, no por su nombre.
    respuesta = _enviar(client, sofia, dra, b'MZ\x90\x00' + b'\x00' * 100, 'foto.jpg')
    assert respuesta.status_code == 302 and AdjuntoMensaje.query.count() == 0 and Mensaje.query.count() == 0
    app.config['ADJUNTO_MAX_MB'] = 0.0001  # ~100 bytes
    try:
        _enviar(client, sofia, dra, PDF + b'x' * 500, 'grande.pdf')
        assert AdjuntoMensaje.query.count() == 0
    finally:
        app.config['ADJUNTO_MAX_MB'] = 5
    # Sin texto ni archivo no se envía nada.
    client.post(f'/mensajes/nino/{sofia.id}/profesional/{dra.id}', data={'contenido': ''})
    assert Mensaje.query.count() == 0


def test_solo_lo_ven_las_partes_de_la_conversacion(client, app):
    _, sofia, dra = _escenario()
    crear_cuidador('otra@test.com')
    otro = crear_profesional('otro@test.com')
    autorizar(sofia, otro)  # autorizado para Sofía, pero no es parte de ESTA conversación
    login(client, 'ana@test.com')
    _enviar(client, sofia, dra, PDF, 'examen.pdf')
    adjunto = AdjuntoMensaje.query.one()
    client.post('/auth/logout')
    for correo in ('otra@test.com', 'otro@test.com'):
        login(client, correo)
        assert client.get(f'/mensajes/adjunto/{adjunto.id}').status_code == 404
        client.post('/auth/logout')
    login(client, 'dra@test.com')
    assert client.get(f'/mensajes/adjunto/{adjunto.id}').status_code == 200


def test_la_supresion_borra_los_archivos(client, app):
    ana, sofia, dra = _escenario()
    login(client, 'ana@test.com')
    _enviar(client, sofia, dra, NOTA_DE_VOZ, 'nota-de-voz.webm')
    ruta = os.path.join(app.config['ADJUNTOS_FOLDER'], AdjuntoMensaje.query.one().archivo)
    assert os.path.exists(ruta)
    client.post('/auth/logout')
    solicitud = SolicitudDerechos(usuario_id=ana.id, usuario_tipo='cuidador', tipo='supresion', nino_id=sofia.id,
                                  descripcion='Quiero que borren los datos.')
    db.session.add(solicitud)
    db.session.commit()
    crear_cuidador('admin@test.com', rol='admin')
    login(client, 'admin@test.com')
    client.post(f'/admin/solicitudes/{solicitud.id}/suprimir', data={'confirmacion': 'ANONIMIZAR'})
    assert not os.path.exists(ruta) and AdjuntoMensaje.query.count() == 0
