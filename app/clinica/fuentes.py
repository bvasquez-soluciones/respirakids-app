"""Fuentes clínicas autorizadas (ver DOCUMENTO_MAESTRO_CONOCIMIENTO_CLINICO_RESPIRAKIDS)."""

DOCUMENTO = 'Herramienta Clínica para el abordaje inicial de las condiciones prevalentes en la primera infancia (AIEPI clínico)'
ENTIDAD = 'Ministerio de Salud y Protección Social de Colombia'

_BASE = 'https://herramientaclinicaprimerainfancia.minsalud.gov.co'

FUENTES = {
    'neumonia': ('Módulo 6 · Neumonía', f'{_BASE}/modulo-6/neumonia/'),
    'bronquiolitis': ('Módulo 6 · Bronquiolitis', f'{_BASE}/modulo-6/bronquiolitis/'),
    'crup': ('Módulo 6 · Laringotraqueitis / CRUP', f'{_BASE}/modulo-6/laringotraqueitis-crup/'),
    'tos_ferina': ('Módulo 6 · Tos ferina', f'{_BASE}/modulo-6/tos-ferina/'),
    'tuberculosis': ('Módulo 6 · Tuberculosis', f'{_BASE}/modulo-6/tuberculosis/'),
    'otitis': ('Módulo 6 · Otitis media aguda', f'{_BASE}/modulo-6/otitis-media-aguda/'),
    'rinofaringitis': ('Módulo 6 · Rinofaringitis aguda', f'{_BASE}/modulo-6/rinofaringitis-aguda/'),
    'fiebre': ('Módulo 5 · Enfermedad febril', f'{_BASE}/modulo-5/enfermedad-febril/'),
    'respirakids': ('Regla de salvaguarda de RespiraKids (no proviene de la fuente)', None),
}


def fuente(clave):
    nombre, url = FUENTES[clave]
    return {'clave': clave, 'nombre': nombre, 'url': url}
