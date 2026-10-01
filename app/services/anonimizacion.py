"""Retira datos identificables del texto antes de enviarlo a servicios externos (asistente IA).

Es una medida de minimización, no una garantía absoluta: por eso el asistente también
advierte al usuario que no escriba datos personales.
"""
import re

_CORREO = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
# Secuencias de 6 o más dígitos, permitiendo espacios, puntos o guiones (documentos, teléfonos).
_NUMERO_LARGO = re.compile(r'(?<!\w)\+?\d(?:[\d .\-]{4,}\d)(?!\w)')
_MINIMO_DIGITOS = 6


def _reemplazar_numero(coincidencia):
    texto = coincidencia.group(0)
    if sum(c.isdigit() for c in texto) >= _MINIMO_DIGITOS:
        return '[número]'
    return texto


def anonimizar(texto, nombres=(), reemplazo_nombre='[nombre]'):
    """Reemplaza correos, números largos y los nombres indicados (palabras completas, sin distinguir mayúsculas)."""
    if not texto:
        return texto
    resultado = _CORREO.sub('[correo]', texto)
    resultado = _NUMERO_LARGO.sub(_reemplazar_numero, resultado)

    palabras = {p.strip() for n in nombres if n for p in n.split() if len(p.strip()) >= 3}
    for palabra in sorted(palabras, key=len, reverse=True):
        resultado = re.sub(rf'(?<!\w){re.escape(palabra)}(?!\w)', reemplazo_nombre, resultado, flags=re.IGNORECASE)
    return resultado
