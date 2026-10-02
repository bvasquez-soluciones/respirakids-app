"""Sistema de diseño: contraste WCAG 2.1 AA de los tokens y ausencia de código en línea en las plantillas."""
import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TOKENS = (RAIZ / 'app/static/css/tokens.css').read_text(encoding='utf-8')
PLANTILLAS = RAIZ / 'app/templates'


def _bloque(selector):
    """Variables --rk-* del primer bloque CSS cuyo selector contiene `selector`."""
    for cabecera, cuerpo in re.findall(r'([^{}]+)\{([^{}]*)\}', TOKENS):
        if selector in cabecera:
            return dict(re.findall(r'(--rk-[\w-]+):\s*([^;]+);', cuerpo))
    raise AssertionError(f'No se encontró el bloque {selector}')


TEMAS = {'oscuro': _bloque(':root[data-theme="dark"]'), 'claro': _bloque(':root[data-theme="light"]')}


def _rgba(valor):
    valor = valor.strip()
    if valor.startswith('#'):
        h = valor[1:]
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (1.0,)
    r, g, b, a = (float(x) for x in re.findall(r'[\d.]+', valor))
    return r, g, b, a


def _sobre(color, fondo):
    """Compone un color (posiblemente translúcido) sobre un fondo opaco."""
    r, g, b, a = color
    return tuple(a * c + (1 - a) * f for c, f in zip((r, g, b), fondo[:3])) + (1.0,)


def _luminancia(c):
    def canal(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(x) for x in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(tema, texto, fondo, base='--rk-surface-solid'):
    t = TEMAS[tema]
    opaco = _sobre(_rgba(t[base]), _rgba(t['--rk-bg']))
    fondo_real = _sobre(_rgba(t[fondo]), opaco)
    color = _sobre(_rgba(t[texto]), fondo_real)
    l1, l2 = sorted((_luminancia(color), _luminancia(fondo_real)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


# (texto, fondo): texto normal, mínimo 4.5:1.
PARES_TEXTO = [
    ('--rk-text', '--rk-surface-solid'), ('--rk-text', '--rk-surface-2'), ('--rk-text', '--rk-bg'),
    ('--rk-text-2', '--rk-surface-solid'), ('--rk-text-2', '--rk-surface-2'),
    ('--rk-muted', '--rk-surface-solid'), ('--rk-muted', '--rk-surface-2'), ('--rk-muted', '--rk-bg'),
    ('--rk-primary-text', '--rk-surface-solid'), ('--rk-primary-text', '--rk-surface-2'),
    ('--rk-primary-text', '--rk-primary-soft'),
    ('--rk-on-primary', '--rk-primary'), ('--rk-on-danger', '--rk-danger'), ('--rk-on-warning', '--rk-warning'),
    ('--rk-success-text', '--rk-success-soft'), ('--rk-ia-text', '--rk-ia-soft'),
    ('--rk-danger-text', '--rk-danger-soft'), ('--rk-warning-text', '--rk-warning-soft'),
    ('--rk-sem-rojo-text', '--rk-sem-rojo-bg'), ('--rk-sem-amarillo-text', '--rk-sem-amarillo-bg'),
    ('--rk-sem-verde-text', '--rk-sem-verde-bg'), ('--rk-sem-neutro-text', '--rk-sem-neutro-bg'),
    ('--rk-text', '--rk-sem-rojo-bg'), ('--rk-text', '--rk-sem-amarillo-bg'), ('--rk-text', '--rk-sem-verde-bg'),
]
# Indicadores gráficos (iconos del semáforo, foco, bordes de acción): mínimo 3:1 (WCAG 1.4.11).
PARES_GRAFICOS = [
    ('--rk-primary', '--rk-surface-solid'), ('--rk-ia', '--rk-surface-solid'),
    ('--rk-sem-rojo', '--rk-surface-solid'), ('--rk-sem-amarillo', '--rk-surface-solid'),
    ('--rk-sem-verde', '--rk-surface-solid'), ('--rk-sem-neutro', '--rk-surface-solid'),
    ('--rk-sem-rojo', '--rk-sem-rojo-bg'), ('--rk-sem-amarillo', '--rk-sem-amarillo-bg'),
    ('--rk-sem-verde', '--rk-sem-verde-bg'),
]


@pytest.mark.parametrize('tema', TEMAS)
@pytest.mark.parametrize('texto,fondo', PARES_TEXTO)
def test_contraste_de_texto_aa(tema, texto, fondo):
    assert contraste(tema, texto, fondo) >= 4.5, f'{tema}: {texto} sobre {fondo} = {contraste(tema, texto, fondo):.2f}'


@pytest.mark.parametrize('tema', TEMAS)
@pytest.mark.parametrize('grafico,fondo', PARES_GRAFICOS)
def test_contraste_de_indicadores(tema, grafico, fondo):
    assert contraste(tema, grafico, fondo) >= 3, f'{tema}: {grafico} sobre {fondo} = {contraste(tema, grafico, fondo):.2f}'


def test_ambos_temas_definen_los_mismos_tokens_de_color():
    assert set(TEMAS['oscuro']) == set(TEMAS['claro'])


def _plantillas_web():
    # reporte_pdf.html lo procesa xhtml2pdf y los correos los muestran clientes de correo (no aplican la CSP
    # y solo entienden estilos en línea).
    return [p for p in PLANTILLAS.rglob('*.html')
            if p.name != 'reporte_pdf.html' and p.parent.name != 'correo']


def test_plantillas_sin_scripts_ni_estilos_en_linea():
    """Permite una política CSP sin 'unsafe-inline': todo el JS y el CSS viven en /static."""
    problemas = []
    for ruta in _plantillas_web():
        html = ruta.read_text(encoding='utf-8')
        nombre = ruta.relative_to(PLANTILLAS)
        # Solo se admiten <script src=...> y bloques de datos JSON (no ejecutables).
        for etiqueta in re.findall(r'<script\b[^>]*>', html):
            if 'src=' not in etiqueta and 'application/json' not in etiqueta:
                problemas.append(f'{nombre}: script en línea')
        if re.search(r'<style\b', html):
            problemas.append(f'{nombre}: bloque <style>')
        if re.search(r'\sstyle="', html):
            problemas.append(f'{nombre}: atributo style')
        if re.search(r'\son[a-z]+="', html):
            problemas.append(f'{nombre}: manejador de evento en línea')
    assert not problemas, '\n'.join(problemas)


def test_hojas_de_estilo_usan_solo_tokens_de_color():
    """Los colores se definen una sola vez (tokens.css); el resto de hojas usan var(--rk-*)."""
    problemas = []
    for ruta in (RAIZ / 'app/static/css').glob('*.css'):
        if ruta.name == 'tokens.css':
            continue
        css = re.sub(r'/\*.*?\*/', '', ruta.read_text(encoding='utf-8'), flags=re.S)
        # Se admite rgba(var(--rk-*-rgb), alfa): es un token con transparencia.
        for color in re.findall(r'#[0-9a-fA-F]{3,8}\b|rgba?\((?!var\()[^)]*\)', css):
            problemas.append(f'{ruta.name}: {color}')
    assert not problemas, '\n'.join(problemas)


def test_csp_no_permite_codigo_en_linea():
    from app import CSP
    assert "'unsafe-inline'" not in CSP['script-src']
    assert "'unsafe-inline'" not in CSP['style-src']
