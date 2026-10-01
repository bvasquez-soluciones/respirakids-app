"""Base de conocimiento del asistente: importación del documento maestro y búsqueda de fragmentos.

El documento maestro (docs/fuentes/DOCUMENTO_MAESTRO_CONOCIMIENTO_CLINICO_RESPIRAKIDS_FINAL.md) es la
ÚNICA fuente autorizada para poblar `conocimientos_sanitarios` (nota final del documento). Cada fragmento
importado conserva el enlace a la página oficial de la que proviene.
"""
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import date

import click
from flask.cli import AppGroup

from app import db
from app.models import ConocimientoSanitario, FuenteConocimiento

RUTA_DOCUMENTO = os.path.join('docs', 'fuentes', 'DOCUMENTO_MAESTRO_CONOCIMIENTO_CLINICO_RESPIRAKIDS_FINAL.md')
NO_DISPONIBLE = 'NO DISPONIBLE EN LA FUENTE CONSULTADA'
SOLO_PROFESIONAL = 'solo_profesional'

# Sección del documento -> tipo de contenido. Las marcadas como profesionales nunca se muestran a cuidadores.
SECCIONES = {
    'definición': ('definicion', False),
    'signos y síntomas': ('signos_sintomas', False),
    'signos y síntomas / criterios o características clínicas': ('signos_sintomas', False),
    'criterios o características clínicas': ('criterios', False),
    'clasificación clínica/semaforización': ('clasificacion', False),
    'factores de riesgo': ('factores_riesgo', False),
    'factores de riesgo / predictores': ('factores_riesgo', False),
    'manejo': ('manejo', True),
    'cuidados en casa': ('cuidados_casa', False),
    'recomendaciones': ('recomendaciones', False),
    'medidas no farmacológicas': ('medidas_no_farmacologicas', False),
    'signos de alarma': ('signos_alarma', False),
    'cuándo consultar': ('cuando_consultar', False),
    'seguimiento': ('seguimiento', False),
    'complicaciones mencionadas': ('complicaciones', False),
    'educación al cuidador': ('educacion', False),
    'tratamiento farmacológico': ('farmacologico', True),
    'dosis': ('dosis', True),
}
TIPOS_ALARMA = {'signos_alarma', 'cuando_consultar'}

# Cualquier fragmento que mencione medicamentos o dosis queda restringido a profesionales, aunque esté en
# una sección general (p. ej. "Recomendaciones" de tos ferina menciona antibióticos).
_PATRON_FARMACOS = re.compile(
    r'antibi[oó]tic|\bmg\b|mg/kg|ui/kg|salbutamol|prednisolona|ampicilina|amikacina|gentamicina|penicilina|'
    r'azitromicina|claritromicina|eritromicina|isoniacida|budesonida|esteroide|adrenalina|cefotaxima|'
    r'ceftriaxona|cefalosporina|tms-smx|aminogluc', re.IGNORECASE)


@dataclass
class Fragmento:
    categoria: str
    condicion: str
    seccion: str
    tipo: str
    contenido: str
    url: str
    solo_profesional: bool


def _slug(texto):
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '_', texto).strip('_')


def leer_documento(ruta=RUTA_DOCUMENTO):
    """Convierte el documento maestro en fragmentos (una sección de una condición = un fragmento).

    Solo se leen las condiciones (secciones numeradas con subsecciones "###" y una "### Fuente").
    Las secciones marcadas como NO DISPONIBLE no se importan: su ausencia hace que el asistente
    responda que la información no está disponible en la fuente.
    """
    with open(ruta, encoding='utf-8') as archivo:
        texto = archivo.read()

    fragmentos = []
    for bloque in re.split(r'^## \d+\. ', texto, flags=re.MULTILINE)[1:]:
        titulo, _, cuerpo = bloque.partition('\n')
        condicion = titulo.strip()
        secciones = re.split(r'^### ', cuerpo, flags=re.MULTILINE)[1:]
        url_fuente = None
        for seccion in secciones:
            nombre, _, contenido = seccion.partition('\n')
            if nombre.strip().lower() == 'fuente':
                coincidencia = re.search(r'https?://\S+', contenido)
                url_fuente = coincidencia.group(0) if coincidencia else None
        if not url_fuente:
            continue  # no es una condición clínica (p. ej. "Fuente y alcance", "Tabla maestra")

        for seccion in secciones:
            nombre, _, contenido = seccion.partition('\n')
            nombre = nombre.strip()
            clave = SECCIONES.get(nombre.lower())
            if not clave:
                continue
            contenido = re.sub(r'\*\*Fuente:\*\*.*', '', contenido).strip()
            if not contenido or NO_DISPONIBLE in contenido:
                continue
            tipo, profesional = clave
            fragmentos.append(Fragmento(
                categoria=_slug(condicion), condicion=condicion, seccion=nombre, tipo=tipo,
                contenido=contenido, url=url_fuente,
                solo_profesional=profesional or bool(_PATRON_FARMACOS.search(contenido)),
            ))
    return fragmentos


def importar_documento(ruta=RUTA_DOCUMENTO):
    """Importa el documento maestro y desactiva (sin borrar) todo contenido que no provenga de él.

    Es idempotente: volver a ejecutarlo actualiza los fragmentos existentes.
    Devuelve un resumen con los conteos.
    """
    fragmentos = leer_documento(ruta)
    hoy = date.today()

    activos_previos = [c.id for c in ConocimientoSanitario.query.filter(ConocimientoSanitario.activo.isnot(False))]
    ConocimientoSanitario.query.update({ConocimientoSanitario.activo: False}, synchronize_session=False)

    fuentes = {}
    creados = actualizados = 0
    for f in fragmentos:
        fuente = fuentes.get(f.url) or FuenteConocimiento.query.filter_by(url=f.url).first()
        if fuente is None:
            fuente = FuenteConocimiento(
                nombre=f'Ministerio de Salud y Protección Social - Herramienta Clínica Primera Infancia · {f.condicion}',
                tipo='Fuente institucional', url=f.url,
            )
            db.session.add(fuente)
            db.session.flush()
        fuentes[f.url] = fuente

        titulo = f'{f.condicion} · {f.seccion}'
        entrada = ConocimientoSanitario.query.filter_by(categoria=f.categoria, titulo=titulo).first()
        if entrada is None:
            entrada = ConocimientoSanitario(categoria=f.categoria, titulo=titulo)
            db.session.add(entrada)
            creados += 1
        else:
            actualizados += 1
        entrada.fuente_id = fuente.id
        entrada.tipo_contenido = f.tipo
        entrada.nivel = 'alarma' if f.tipo in TIPOS_ALARMA else 'basico'
        entrada.contenido = f.contenido
        entrada.restricciones = SOLO_PROFESIONAL if f.solo_profesional else None
        entrada.fecha_actualizacion = hoy
        entrada.activo = True

    db.session.commit()
    return {
        'fragmentos': len(fragmentos), 'creados': creados, 'actualizados': actualizados,
        'solo_profesional': sum(f.solo_profesional for f in fragmentos),
        'activos_previos': activos_previos,
    }


# ---------------------------------------------------------------- Búsqueda

_STOPWORDS = set('''
a al algo como con cual cuales cuando de del el en es esta este esto hay la las le lo los me mi mis muy no
o para pero por porque puede puedo que se si sin su sus te tengo tiene un una uno y ya hijo hija nino nina
bebe mi debo hacer hago esta estan son ser estar sobre tipo tipos cosas
'''.split())

# Palabras cotidianas del cuidador -> vocabulario del documento.
_SINONIMOS = {
    'gripa': 'rinofaringitis resfriado', 'gripe': 'rinofaringitis resfriado', 'resfriado': 'rinofaringitis',
    'moco': 'rinorrea secrecion', 'mocos': 'rinorrea secrecion', 'calentura': 'fiebre temperatura',
    'ahogo': 'dificultad respiratoria', 'ahoga': 'dificultad respiratoria', 'silbido': 'sibilancias',
    'silba': 'sibilancias', 'pecho': 'sibilancias torax', 'morado': 'cianosis', 'azul': 'cianosis',
    'azulado': 'cianosis', 'mollera': 'fontanela', 'costillas': 'tiraje subcostal', 'hunde': 'tiraje',
    'oido': 'otitis', 'oreja': 'otitis', 'garganta': 'faringoamigdalitis faringe', 'amigdalas': 'faringoamigdalitis',
    'tosferina': 'tos ferina', 'perruna': 'crup laringotraqueitis', 'disfonia': 'crup', 'ronco': 'crup disfonica',
    'tb': 'tuberculosis', 'prevenir': 'prevencion recomendaciones', 'prevencion': 'recomendaciones medidas',
    'urgencias': 'consultar alarma', 'alarma': 'signos alarma', 'grave': 'gravedad alarma',
    'rapido': 'taquipnea frecuencia respiratoria', 'rapida': 'taquipnea frecuencia respiratoria',
}

_INTENCIONES = (
    (re.compile(r'cuando (debo |hay que |se debe )?(consultar|llevar|ir)|urgencia|alarma|grave|peligr'), TIPOS_ALARMA),
    (re.compile(r'que es|que significa|definicion'), {'definicion'}),
    (re.compile(r'prevenir|prevencion|evitar|contagi'), {'recomendaciones', 'medidas_no_farmacologicas'}),
    (re.compile(r'sintoma|signo|como se si|como saber'), {'signos_sintomas', 'signos_alarma'}),
    (re.compile(r'en casa|cuidado'), {'cuidados_casa', 'medidas_no_farmacologicas'}),
)


def normalizar(texto):
    texto = unicodedata.normalize('NFKD', texto or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', texto).strip()


def _raiz(palabra):
    return palabra[:6] if len(palabra) > 6 else palabra


def _terminos(texto):
    """Términos de la pregunta y, aparte, los que vienen de sinónimos del vocabulario de la fuente."""
    palabras = [p for p in normalizar(texto).split() if p not in _STOPWORDS and len(p) > 2]
    sinonimos = set()
    for p in palabras:
        sinonimos |= {_raiz(s) for s in normalizar(_SINONIMOS.get(p, '')).split()}
    return {_raiz(p) for p in palabras}, sinonimos


def buscar(pregunta, incluir_profesional=False, limite=4, puntaje_minimo=2):
    """Fragmentos activos más relevantes para la pregunta, de mayor a menor puntaje."""
    propios, sinonimos = _terminos(pregunta)
    terminos = propios | sinonimos
    if not terminos:
        return []
    pregunta_normal = normalizar(pregunta)
    tipos_buscados = set().union(*[tipos for patron, tipos in _INTENCIONES if patron.search(pregunta_normal)])

    consulta = ConocimientoSanitario.query.filter(ConocimientoSanitario.activo.is_(True))
    if not incluir_profesional:
        consulta = consulta.filter(
            (ConocimientoSanitario.restricciones.is_(None)) | (ConocimientoSanitario.restricciones != SOLO_PROFESIONAL)
        )

    puntuados = []
    for entrada in consulta.all():
        en_titulo = {_raiz(p) for p in normalizar(entrada.titulo + ' ' + entrada.categoria).split()}
        en_contenido = {_raiz(p) for p in normalizar(entrada.contenido).split()}
        # Los sinónimos son equivalencias deliberadas con el vocabulario de la fuente: pesan más.
        puntaje = (3 * len(terminos & en_titulo) + len(propios & en_contenido)
                   + 2 * len((sinonimos - propios) & en_contenido))
        if puntaje and entrada.tipo_contenido in tipos_buscados:
            puntaje += 3
        if puntaje >= puntaje_minimo:
            puntuados.append((puntaje, entrada))
    puntuados.sort(key=lambda par: (-par[0], par[1].id))
    return [entrada for _, entrada in puntuados[:limite]]


# ---------------------------------------------------------------- Comando

conocimiento_cli = AppGroup('conocimiento', help='Base de conocimiento del asistente.')


@conocimiento_cli.command('importar')
def importar():
    """Importa el documento maestro y desactiva el contenido que no proviene de él."""
    from app.services.auditoria import registrar_actividad
    resumen = importar_documento()
    registrar_actividad('importar_conocimiento', 'conocimiento', None, detalles={
        'documento': RUTA_DOCUMENTO, 'fragmentos': resumen['fragmentos'],
        'ids_activos_antes_de_importar': resumen['activos_previos'],
    })
    click.echo(f"Fragmentos importados: {resumen['fragmentos']} (nuevos: {resumen['creados']}, "
               f"actualizados: {resumen['actualizados']}, solo para profesionales: {resumen['solo_profesional']}).")
    click.echo(f"Entradas que estaban activas antes de importar: {len(resumen['activos_previos'])} "
               '(quedan desactivadas si no provienen del documento; sus ids quedan en logs_actividad).')
