"""Adjuntos de los mensajes: imágenes, documentos PDF y notas de voz.

Medidas de seguridad (son datos de salud de menores):
- El tipo se decide por el CONTENIDO del archivo (firma de los primeros bytes), no por su extensión ni por lo que
  declara el navegador: un ejecutable renombrado a .jpg se rechaza.
- Las imágenes se vuelven a codificar: se eliminan los metadatos EXIF (que suelen incluir la ubicación GPS) y
  cualquier contenido oculto; además se reducen a un tamaño razonable.
- Se guardan con un nombre aleatorio en ADJUNTOS_FOLDER (privada, fuera de /static); el nombre original solo se
  conserva como texto para mostrarlo.
- Tamaño máximo: ADJUNTO_MAX_MB.
"""
import io
import os
import re
import uuid

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError

from app import db
from app.models import AdjuntoMensaje

LADO_MAXIMO_IMAGEN = 2000  # píxeles


class AdjuntoInvalido(ValueError):
    """Mensaje pensado para mostrarse al usuario."""


def _carpeta():
    carpeta = current_app.config['ADJUNTOS_FOLDER']
    os.makedirs(carpeta, mode=0o700, exist_ok=True)
    return carpeta


def ruta(adjunto):
    return os.path.join(current_app.config['ADJUNTOS_FOLDER'], adjunto.archivo)


def _firma(datos):
    """(tipo, mime, extensión) según los primeros bytes, o None si no es un formato permitido."""
    if datos.startswith(b'%PDF-'):
        return 'documento', 'application/pdf', 'pdf'
    if datos.startswith(b'\x1aE\xdf\xa3'):  # Matroska/WebM (Chrome, Firefox, Edge, Android)
        return 'audio', 'audio/webm', 'webm'
    if datos.startswith(b'OggS'):
        return 'audio', 'audio/ogg', 'ogg'
    if datos[4:8] == b'ftyp':  # MP4/M4A (Safari en iPhone y Mac)
        return 'audio', 'audio/mp4', 'm4a'
    if datos.startswith(b'ID3') or datos[:2] in (b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'):
        return 'audio', 'audio/mpeg', 'mp3'
    if datos.startswith(b'RIFF') and datos[8:12] == b'WAVE':
        return 'audio', 'audio/wav', 'wav'
    if datos.startswith((b'\xff\xd8\xff', b'\x89PNG\r\n\x1a\n')) or (datos.startswith(b'RIFF') and datos[8:12] == b'WEBP'):
        return 'imagen', 'image/jpeg', 'jpg'  # toda imagen se guarda re-codificada como JPEG
    return None


def _nombre_seguro(nombre, extension):
    base = os.path.splitext(os.path.basename(nombre or ''))[0]
    base = re.sub(r'[^\w\- ]', '', base, flags=re.UNICODE).strip()[:100] or 'archivo'
    return f'{base}.{extension}'


def _reencodear_imagen(datos):
    try:
        imagen = Image.open(io.BytesIO(datos))
        imagen.verify()
        imagen = Image.open(io.BytesIO(datos))
        imagen = ImageOps.exif_transpose(imagen)  # respeta la orientación antes de descartar el EXIF
    except (UnidentifiedImageError, OSError, ValueError):
        raise AdjuntoInvalido('La imagen está dañada o no es válida.')
    imagen = imagen.convert('RGB')
    imagen.thumbnail((LADO_MAXIMO_IMAGEN, LADO_MAXIMO_IMAGEN))
    salida = io.BytesIO()
    imagen.save(salida, 'JPEG', quality=85, optimize=True)  # sin exif=: no se copia ningún metadato
    return salida.getvalue()


def guardar(archivo, mensaje):
    """Valida y guarda el archivo subido (FileStorage) como adjunto del mensaje. Lanza AdjuntoInvalido."""
    maximo = int(current_app.config['ADJUNTO_MAX_MB'] * 1024 * 1024)
    datos = archivo.read(maximo + 1)
    if not datos:
        raise AdjuntoInvalido('El archivo está vacío.')
    if len(datos) > maximo:
        raise AdjuntoInvalido(f'El archivo no puede superar {current_app.config["ADJUNTO_MAX_MB"]} MB.')
    firma = _firma(datos[:16])
    if firma is None:
        raise AdjuntoInvalido('Formato no permitido. Puedes enviar fotos (JPG, PNG, WebP), documentos PDF o notas de voz.')
    tipo, mime, extension = firma
    if tipo == 'imagen':
        datos = _reencodear_imagen(datos)

    nombre_disco = f'{uuid.uuid4().hex}.{extension}'
    with open(os.path.join(_carpeta(), nombre_disco), 'wb') as destino:
        destino.write(datos)
    adjunto = AdjuntoMensaje(mensaje=mensaje, tipo=tipo, mime=mime, archivo=nombre_disco, tamano=len(datos),
                             nombre_original=_nombre_seguro(archivo.filename, extension))
    db.session.add(adjunto)
    return adjunto


def eliminar_de_mensajes(mensajes):
    """Borra del disco y de la base los adjuntos de los mensajes indicados (supresión de datos)."""
    for mensaje in mensajes:
        for adjunto in list(mensaje.adjuntos):
            try:
                os.remove(ruta(adjunto))
            except FileNotFoundError:
                pass
            db.session.delete(adjunto)


def tamano_legible(bytes_):
    return f'{bytes_ / 1024:.0f} KB' if bytes_ < 1024 * 1024 else f'{bytes_ / 1024 / 1024:.1f} MB'
