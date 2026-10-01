"""Orquestación del asistente: decide cómo responder y garantiza que la respuesta se base en la fuente.

Orden de decisión para cada pregunta:
1. Si describe signos de alarma -> se antepone un aviso fijo de buscar atención (no depende de la IA).
2. Si un cuidador pide medicamentos o dosis -> respuesta fija: RespiraKids no recomienda medicamentos.
3. Se buscan fragmentos del documento maestro. Si no hay -> "NO DISPONIBLE EN LA FUENTE CONSULTADA".
4. Con fragmentos: la IA redacta usando SOLO esos fragmentos y cita [n]. Si la IA no está disponible o
   su respuesta no cita la fuente, se muestran los fragmentos textuales (respuesta extractiva).
"""
import re
from dataclasses import dataclass, field

from app.asistente.conocimiento import NO_DISPONIBLE, buscar, normalizar
from app.asistente_ia import generar_respuesta_fundamentada

TIPO_GENERADA = 'generada'
TIPO_EXTRACTIVA = 'extractiva'
TIPO_NO_DISPONIBLE = 'no_disponible'
TIPO_MEDICAMENTOS = 'medicamentos'

# Signos de alarma descritos en la fuente (Módulos 5 y 6), en palabras de un cuidador.
_PATRON_ALARMA = re.compile(
    r'no (puede|quiere|logra) (beber|tomar|tragar)|convuls|morad|azul|costillas|se le hunde|tiraje|quejid|'
    r'no respira|deja de respirar|pausas? (en|al) (la )?respira|apnea|aleteo|rigid|mollera|fontanela|'
    r'manchas (rojas|moradas)|petequia|no despierta|dificil (de )?despertar|inconscien|desmay|estridor'
)
AVISO_ALARMA = ('⚠️ Atención: lo que describes coincide con signos que la fuente clínica considera de alarma. '
                'Busca atención en un servicio de salud de inmediato; no esperes la respuesta del asistente.')

_PATRON_MEDICAMENTOS = re.compile(
    r'dosis|\bmg\b|miligramo|medicamento|medicina|jarabe|pastilla|gotas|antibiotic|acetaminofen|paracetamol|'
    r'ibuprofeno|salbutamol|inhalador|que le (doy|puedo dar)|cuanto le doy|automedic'
)
RESPUESTA_MEDICAMENTOS = (
    'RespiraKids no recomienda medicamentos ni dosis. Solo un profesional de salud que valore al niño o niña puede '
    'indicarlos. Si un profesional ya le indicó un tratamiento, lo encontrarás en la ficha del niño/a dentro de '
    'RespiraKids. Ante signos de alarma, busca atención en un servicio de salud de inmediato.'
)

RESPUESTA_NO_DISPONIBLE = (
    f'{NO_DISPONIBLE}. La base de conocimiento de RespiraKids solo contiene la información de la Herramienta '
    'Clínica de primera infancia (AIEPI) del Ministerio de Salud y Protección Social, y no encontré ahí una respuesta '
    'a tu pregunta. Si tienes dudas sobre la salud del niño o niña, consulta a un profesional de salud.'
)


@dataclass
class RespuestaAsistente:
    texto: str
    tipo: str
    fuentes: list = field(default_factory=list)   # dicts: n, titulo, url
    alarma: bool = False

    def como_dict(self):
        return {'respuesta': self.texto, 'tipo': self.tipo, 'fuentes': self.fuentes, 'alarma': self.alarma}


def _fuentes(fragmentos):
    return [{'n': i, 'titulo': f.titulo, 'url': f.fuente.url if f.fuente else None}
            for i, f in enumerate(fragmentos, start=1)]


def _extractiva(fragmentos):
    partes = ['Esto es lo que dice la fuente clínica sobre tu pregunta:']
    for i, f in enumerate(fragmentos, start=1):
        partes.append(f'- **{f.titulo}** [{i}]: {f.contenido}')
    return '\n'.join(partes)


def _cita_la_fuente(texto, total):
    citas = {int(n) for n in re.findall(r'\[(\d+)\]', texto)}
    return bool(citas) and citas <= set(range(1, total + 1))


def responder(pregunta, es_profesional=False, contexto=None, historial=None):
    """Respuesta del asistente a una pregunta (ya anonimizada)."""
    texto_normal = normalizar(pregunta)
    alarma = bool(_PATRON_ALARMA.search(texto_normal))

    if not es_profesional and _PATRON_MEDICAMENTOS.search(texto_normal):
        respuesta = RespuestaAsistente(RESPUESTA_MEDICAMENTOS, TIPO_MEDICAMENTOS, alarma=alarma)
    else:
        consulta = pregunta + (' ' + ' '.join(contexto.get('senales', [])) if contexto else '')
        fragmentos = buscar(consulta, incluir_profesional=es_profesional)
        if not fragmentos:
            respuesta = RespuestaAsistente(RESPUESTA_NO_DISPONIBLE, TIPO_NO_DISPONIBLE, alarma=alarma)
        else:
            generado = generar_respuesta_fundamentada(pregunta, fragmentos, contexto=contexto, historial=historial)
            if generado and (_cita_la_fuente(generado, len(fragmentos)) or NO_DISPONIBLE in generado):
                respuesta = RespuestaAsistente(generado, TIPO_GENERADA, _fuentes(fragmentos), alarma)
            else:
                respuesta = RespuestaAsistente(_extractiva(fragmentos), TIPO_EXTRACTIVA, _fuentes(fragmentos), alarma)

    if alarma:
        respuesta.texto = f'{AVISO_ALARMA}\n{respuesta.texto}'
    return respuesta
