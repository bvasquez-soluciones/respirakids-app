"""Genera el documento de validación clínica a partir de las reglas en código (fuente única).

    flask reglas documentar      -> escribe docs/REGLAS_CLINICAS_v1.md
"""
import os

import click
from flask.cli import AppGroup

from app.clinica import reglas_v1
from app.clinica.fuentes import DOCUMENTO, ENTIDAD, FUENTES

RUTA_DOCUMENTO = os.path.join('docs', 'REGLAS_CLINICAS_v1.md')
NIVEL_TEXTO = {'rojo': '🔴 Rojo', 'amarillo': '🟡 Amarillo'}


def generar_markdown():
    lineas = [
        f'# Reglas clínicas {reglas_v1.VERSION} — documento de validación',
        '',
        '> **Estado: PENDIENTE DE VALIDACIÓN POR UN PROFESIONAL DE SALUD.** Este documento se genera '
        'automáticamente desde `app/clinica/reglas_v1.py` con `flask reglas documentar`; no editarlo a mano.',
        '',
        f'**Fuente clínica principal:** {DOCUMENTO}, {ENTIDAD}.',
        '',
        '## 1. Convención de semaforización (decisión principal a validar)',
        '',
        'La fuente **no define** una semaforización verde/amarillo/rojo (documento maestro, sección 15). '
        'RespiraKids aplica esta convención única:',
        '',
        '| Nivel | Se asigna cuando la fuente describe el hallazgo como… |',
        '|---|---|',
        '| 🔴 Rojo | signo de alarma, de gravedad o de máxima gravedad, o indica hospitalización o remisión hospitalaria |',
        '| 🟡 Amarillo | criterio para consultar o canalizar, o una clasificación no grave (p. ej. "Neumonía", "Tos ferina") |',
        '| 🟢 Verde | no se identificó ninguno de los criterios anteriores (no significa "sano") |',
        '',
        'El nivel final es el mayor de las reglas que se cumplen. Las reglas marcadas como **salvaguarda** no '
        'provienen de la fuente.',
        '',
        '## 2. Reglas implementadas',
        '',
    ]
    for regla in reglas_v1.REGLAS:
        nombre_fuente, url = FUENTES[regla.fuente]
        fuente = f'[{nombre_fuente}]({url})' if url else nombre_fuente
        lineas += [
            f'### {regla.id} · {NIVEL_TEXTO[regla.nivel]} · {regla.senal}',
            '',
            f'- **Origen:** {"⚠️ Salvaguarda de RespiraKids (NO proviene de la fuente)" if regla.origen == "salvaguarda" else "Fuente clínica"}',
            f'- **Fuente:** {fuente}',
            f'- **Criterio:** {regla.criterio}',
            f'- **Orientación mostrada:** {regla.orientacion}',
            '- **Puntos a validar:**',
        ]
        lineas += [f'  - [ ] {punto}' for punto in regla.validacion]
        lineas += ['- **Decisión del profesional:** ☐ Aprobada ☐ Aprobada con cambios ☐ Rechazada — Observaciones: ______', '']

    lineas += [
        '## 3. Umbrales usados (copiados de la fuente)',
        '',
        '**Respiración rápida (Módulo 6 · Neumonía):** <2 meses >60; 3-12 meses >50; 1-5 años >40 respiraciones por '
        'minuto, medidas durante 1 minuto con el niño despierto y sin llorar.',
        '',
        '**Hipoxemia según altitud (Módulo 6 · Neumonía):** 0-1500 msnm ≤94 %; 1501-2000 ≤92 %; 2001-2500 ≤90 %; '
        '2501-3000 ≤88 %; 3500-4000 ≤83 %.',
        '',
        '## 4. Criterios de la fuente que no se implementaron',
        '',
        '| Criterio | Motivo |',
        '|---|---|',
    ]
    lineas += [f'| {criterio} | {motivo} |' for criterio, motivo in reglas_v1.NO_IMPLEMENTABLES]
    lineas += [
        '',
        '## 5. Firma de validación',
        '',
        'Una vez validadas todas las reglas, el profesional firma esta versión y el equipo técnico define '
        f'`REGLAS_CLINICAS_VALIDADAS={reglas_v1.VERSION}` en producción. Sin esa variable la aplicación no arranca '
        'en producción.',
        '',
        '- Nombre del profesional: ______________________',
        '- Profesión y registro (RETHUS / tarjeta profesional): ______________________',
        '- Fecha: ______________________',
        '- Firma: ______________________',
        '',
    ]
    return '\n'.join(lineas)


reglas_cli = AppGroup('reglas', help='Herramientas del motor clínico.')


@reglas_cli.command('documentar')
def documentar():
    """Genera docs/REGLAS_CLINICAS_v1.md a partir de las reglas en código."""
    os.makedirs(os.path.dirname(RUTA_DOCUMENTO), exist_ok=True)
    with open(RUTA_DOCUMENTO, 'w', encoding='utf-8', newline='\n') as archivo:
        archivo.write(generar_markdown())
    click.echo(f'Documento generado: {RUTA_DOCUMENTO}')
