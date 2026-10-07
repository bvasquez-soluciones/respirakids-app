"""Guía interactiva para usuarios nuevos (cuidadores y profesionales): ilumina el botón a usar y explica qué hacer.

La etapa se deduce de lo que el cuidador ya hizo (no se guarda nada en la base de datos):
  registrar_nino     -> aún no tiene niños/as activos
  autorizar          -> sus niños/as no tienen la autorización de datos de salud
  registrar_sintomas -> puede registrar síntomas pero aún no hay ninguna evaluación
  primer_resultado   -> está viendo su primera evaluación (cierre de la guía)
  recorrido          -> la pidió de nuevo desde Ayuda (?guia=1) cuando ya completó lo anterior

Cada paso apunta a un elemento con `data-guia="<clave>"` en las plantillas; static/js/guia.js los recorre.
Si el elemento no está en la página, ese paso se omite.
"""
from flask import current_app, request

from app.models import Evaluacion, Nino

# Pantallas donde la guía puede aparecer, por rol.
ENDPOINTS = {'dashboard.cuidador', 'pacientes.listar', 'pacientes.nuevo', 'pacientes.consentimiento',
             'sintomas.nuevo', 'sintomas.resultado'}
ENDPOINTS_PROFESIONAL = {'dashboard.ajustes', 'dashboard.profesional', 'mensajes.solicitudes'}

BIENVENIDA = {
    'titulo': '¡Bienvenido a RespiraKids! 👋',
    'texto': 'Te vamos a guiar paso a paso para que puedas registrar a los niños y realizar su seguimiento.',
}


def _paso(objetivo, titulo, texto, accion=False, nino=None):
    """`accion=True`: el cuidador debe presionar el elemento iluminado para continuar (no hay botón Siguiente)."""
    paso = {'objetivo': objetivo, 'titulo': titulo, 'texto': texto, 'accion': accion}
    if nino is not None:
        paso['nino'] = nino.id
    return paso


def _articulo(nino):
    return 'tu niña' if nino.sexo == 'F' else 'tu niño'


def etapa(cuidador):
    """(etapa, niño/a de referencia) según lo que el cuidador ya hizo; (None, None) si la guía terminó."""
    ninos = (Nino.query.filter_by(cuidador_id=cuidador.id, estado='activo')
             .order_by(Nino.fecha_registro, Nino.id).all())
    if not ninos:
        return 'registrar_nino', None
    ids = [n.id for n in ninos]
    if Evaluacion.query.filter(Evaluacion.nino_id.in_(ids)).first() is not None:
        return None, None
    con_autorizacion = [n for n in ninos if n.consentimiento_otorgado]
    if not con_autorizacion:
        return 'autorizar', ninos[0]
    return 'registrar_sintomas', con_autorizacion[0]


def _pasos_registrar_nino(endpoint):
    if endpoint in ('dashboard.cuidador', 'pacientes.listar'):
        return [_paso('registrar-nino', 'Registra a tu niño o niña',
                      'Presiona aquí 👆 para registrar al primer niño o niña que vas a acompañar.', accion=True)]
    if endpoint == 'pacientes.nuevo':
        return _pasos_formulario_nino()
    return []


def _pasos_formulario_nino():
    return [
        _paso('datos-nino', 'Escribe sus datos',
              'Nombres, apellidos, fecha de nacimiento y sexo. Los campos con * son obligatorios; peso y talla son '
              'opcionales.'),
        _paso('autorizacion', 'Autoriza el uso de sus datos de salud',
              'Marca la primera casilla: sin ella no se pueden registrar síntomas. Las otras dos son opcionales y '
              'puedes cambiarlas cuando quieras.'),
        _paso('guardar-nino', 'Dale Guardar',
              'Cuando termines, presiona «Guardar» 👆. Luego te mostramos cómo registrar sus síntomas.', accion=True),
    ]


def _pasos_autorizar(endpoint, nino):
    if endpoint in ('dashboard.cuidador', 'pacientes.listar'):
        return [_paso('autorizar', f'Autoriza los datos de {nino.nombre}',
                      f'Para registrar los síntomas de {_articulo(nino)} primero debes autorizar el tratamiento de '
                      f'sus datos de salud. Presiona aquí 👆.', accion=True, nino=nino)]
    if endpoint == 'pacientes.consentimiento':
        return [
            _paso('autorizacion', 'Marca la autorización',
                  'La primera casilla es necesaria para registrar síntomas; las demás son opcionales.'),
            _paso('guardar-autorizacion', 'Dale Guardar', 'Presiona «Guardar» 👆 para continuar.', accion=True),
        ]
    return []


def _pasos_registrar_sintomas(endpoint, nino):
    if endpoint in ('dashboard.cuidador', 'pacientes.listar'):
        return [_paso('registrar-sintomas', f'¡Muy bien! Ahora registra los síntomas de {nino.nombre}',
                      f'Elige a {_articulo(nino)} y presiona «+ Registrar síntomas» 👆 para contarnos cómo está hoy.',
                      accion=True, nino=nino)]
    if endpoint == 'sintomas.nuevo':
        return [
            _paso('secciones', 'Las secciones del registro',
                  'Aquí ves las secciones y cuántas opciones marcaste en cada una. Tócalas para ir directo.'),
            _paso('grupo-alarma', 'Empieza por los signos de alarma 🚨',
                  'Si ves alguno de estos signos, márcalo y acude de inmediato a un servicio de salud: no esperes el '
                  'resultado.'),
            _paso('grupo-respiracion', 'Toca lo que observes',
                  'Cada síntoma es una tarjeta: tócala y queda marcada con ✓. Solo marca lo que hayas visto; nada es '
                  'obligatorio.'),
            _paso('guardar-sintomas', 'Guarda y mira la orientación',
                  'Cuando termines, presiona «Guardar y ver orientación» 👆.', accion=True),
        ]
    return []


def _pasos_primer_resultado():
    return [
        _paso('estado-resultado', 'Este es el semáforo',
              'Te orienta según la guía AIEPI del Ministerio de Salud: rojo, acude de inmediato a un servicio de salud; '
              'amarillo, consulta a un profesional; verde, sigue observando. Es una orientación, no un diagnóstico.'),
        _paso('hablar-profesional', '¿Tienes dudas? Habla con un profesional',
              'Escribe tu mensaje y presiona aquí: te atiende el primer profesional de la clínica que se conecte.'),
        _paso('menu-ayuda', '¡Listo! 🎉',
              'Ya sabes usar RespiraKids. Vuelve a registrar síntomas cuando notes cambios. Si necesitas ayuda, la '
              'encuentras en el menú, en «Ayuda».'),
    ]


def _pasos_recorrido():
    return [
        _paso('tarjeta-nino', 'La tarjeta de cada niño/a',
              'Muestra el color del semáforo de su última evaluación, las señales y los últimos síntomas. El avatar '
              'cambia según cómo esté.'),
        _paso('seguimiento', '¿Cómo sigue?',
              'Cuéntanos si mejoró, sigue igual o empeoró. Si cambió, te pediremos registrar los síntomas de nuevo.'),
        _paso('registrar-sintomas', 'Registrar síntomas',
              'Úsalo cada vez que notes algo nuevo para recibir una orientación actualizada.'),
        _paso('hablar-profesional-tarjeta', 'Hablar con un profesional',
              'Conecta con un profesional de la clínica por mensajes, con fotos o notas de voz.'),
        _paso('menu-ayuda', 'Ayuda siempre a la mano',
              'En el menú encuentras «Ayuda», con el manual completo y esta guía.'),
    ]


# ---------------------------------------------------------------- Profesionales de salud
# Etapas: clave (primer ingreso con contraseña temporal, en Ajustes), panel (recorrido del panel de pacientes) y
# solicitudes (primera visita a Solicitudes). Las dos últimas quedan marcadas como vistas en el navegador (guia.js).

def _bienvenida_profesional(usuario, texto):
    return {'titulo': f'¡Bienvenido/a a RespiraKids, {usuario.nombre_con_titulo}! 👋', 'texto': texto}


def _pasos_clave():
    return [
        _paso('cambiar-clave', 'Primero, crea tu propia contraseña',
              'Escribe la contraseña temporal que te dio el administrador y tu contraseña nueva (mínimo 8 caracteres, '
              'con letras y números). Luego presiona «Actualizar contraseña».'),
        _paso('perfil-profesional', 'Completa tu perfil',
              'Sube tu foto y escribe tu especialidad: es lo que ven las familias cuando te conectas con ellas. Puedes '
              'hacerlo ahora o más tarde desde «Ajustes».'),
    ]


def _pasos_panel(usuario):
    pasos = [
        _paso('lista-pacientes', 'Todos los pacientes de la clínica',
              'Aquí están todos los niños y niñas con su semáforo, para priorizar: rojo, signos de alarma; amarillo, '
              'vigilancia; verde, sin señales. Toca uno para ver su resumen.'),
        _paso('filtros', 'Busca y filtra',
              'Filtra por color o por «Mis pacientes» (los que te autorizaron) y busca por nombre.'),
        _paso('detalle-paciente', 'Resumen o expediente completo',
              'Todos los profesionales ven el semáforo. El expediente completo (historial, ficha y medicamentos) solo '
              'lo ves si el cuidador te autoriza.'),
        _paso('nav-semaforo', 'Semáforo de la clínica',
              'El conteo de niños por color y la lista ordenada para priorizar.'),
        _paso('nav-solicitudes', 'Solicitudes de atención',
              'Aquí llegan las familias que piden hablar con un profesional. Atiende el caso quien lo toma primero.'),
        _paso('alertas', 'Pacientes en rojo',
              'Este ícono cuenta a tus pacientes autorizados cuya última evaluación quedó en rojo.'),
        _paso('ayuda-pro', '¿Dudas? Aquí está tu manual',
              'El botón «?» abre el manual para profesionales, con buscador y preguntas frecuentes.'),
    ]
    if not (usuario.foto and usuario.especialidad):
        pasos.append(_paso('nav-ajustes', 'Completa tu perfil',
                           'Aún te falta la foto o la especialidad. Las familias las ven al conectarse contigo.'))
    return pasos


def _pasos_solicitudes():
    return [
        _paso('disponibilidad', 'Tu disponibilidad',
              'Mientras estés disponible recibes nuevas solicitudes. Al terminar tu turno, presiona «Pausar nuevas '
              'solicitudes»: tus casos abiertos siguen activos.'),
        _paso('cupo', 'Tu cupo de casos',
              f'Puedes tener hasta {current_app.config["CUPO_CASOS_POR_PROFESIONAL"]} casos abiertos a la vez. Aquí '
              'ves cuántos tienes y cuántas solicitudes esperan en la clínica.'),
        _paso('en-espera', 'Solicitudes en espera',
              'Se ordenan por color (rojo primero) y antigüedad. Presiona «Atender» para tomar el caso y abrir la '
              'conversación con la familia.'),
        _paso('mis-casos', 'Tus casos abiertos',
              'Cuando termines de orientar a la familia, presiona «Cerrar caso» para liberar el cupo. La conversación '
              'queda disponible.'),
    ]


def _pasos_profesional(usuario, endpoint):
    """(etapa, pasos, bienvenida) del profesional en la página actual."""
    if endpoint == 'dashboard.ajustes' and usuario.debe_cambiar_password:
        return 'clave', _pasos_clave(), _bienvenida_profesional(
            usuario, 'Antes de empezar, crea tu propia contraseña y completa tu perfil. Luego te mostramos el panel.')
    if endpoint == 'dashboard.profesional' and not request.args.get('paciente'):
        return 'panel', _pasos_panel(usuario), _bienvenida_profesional(
            usuario, 'Te mostramos en un minuto cómo ver a los pacientes de la clínica por su semáforo y atender las '
                     'solicitudes de las familias.')
    if endpoint == 'mensajes.solicitudes':
        return 'solicitudes', _pasos_solicitudes(), None
    return None, [], None


def pasos_de_la_pagina(usuario):
    """Datos de la guía para la página actual, o None si no corresponde mostrarla."""
    endpoint = request.endpoint
    if not usuario.is_authenticated:
        return None
    if getattr(usuario, 'rol', None) == 'profesional' and endpoint in ENDPOINTS_PROFESIONAL:
        actual, pasos, bienvenida = _pasos_profesional(usuario, endpoint)
        if not pasos:
            return None
        return {'etapa': actual, 'pasos': pasos, 'bienvenida': bienvenida, 'usuario': f'p{usuario.id}',
                'forzada': request.args.get('guia') == '1'}
    if getattr(usuario, 'rol', None) != 'cuidador' or endpoint not in ENDPOINTS:
        return None
    actual, nino = etapa(usuario)
    pasos, bienvenida = [], None

    if actual == 'registrar_nino':
        pasos = _pasos_registrar_nino(endpoint)
        bienvenida = BIENVENIDA if endpoint == 'dashboard.cuidador' else None
    elif actual == 'autorizar':
        pasos = _pasos_autorizar(endpoint, nino)
    elif actual == 'registrar_sintomas':
        pasos = _pasos_registrar_sintomas(endpoint, nino)
    elif endpoint == 'sintomas.resultado':
        ids = [n.id for n in usuario.ninos]
        if ids and Evaluacion.query.filter(Evaluacion.nino_id.in_(ids)).count() == 1:
            actual, pasos = 'primer_resultado', _pasos_primer_resultado()
    elif endpoint == 'dashboard.cuidador' and request.args.get('guia') == '1':
        actual, pasos = 'recorrido', _pasos_recorrido()

    if not pasos:
        return None
    # `forzada`: la pidió desde Ayuda; se muestra aunque antes la haya saltado.
    return {'etapa': actual, 'pasos': pasos, 'bienvenida': bienvenida, 'usuario': f'c{usuario.id}',
            'forzada': request.args.get('guia') == '1'}
