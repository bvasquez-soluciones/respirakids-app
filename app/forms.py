"""Formularios y validación del lado del servidor.

Reglas que siguen todos los formularios de RespiraKids:
- Cada campo define aquí su etiqueta, si es obligatorio y sus atributos HTML (autocomplete,
  maxlength, placeholder). Los templates los dibujan con las macros de
  `templates/macros/formularios.html`, que marcan con * los obligatorios a partir de esta
  misma definición; así la interfaz y la validación nunca se contradicen.
- La validación del navegador es solo una ayuda: la validación que cuenta es la del servidor.
- Los textos se normalizan (espacios sobrantes, correo en minúsculas) antes de validarse.
- Los mensajes de error explican cómo corregir el dato, en lenguaje sencillo.
"""
import re
from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField, DateField, DateTimeLocalField, DecimalField, EmailField, FieldList, FloatField, Form,
    FormField, IntegerField, PasswordField, SelectField, StringField, TelField, TextAreaField,
)
from wtforms.validators import (
    DataRequired, Email, EqualTo, InputRequired, Length, NumberRange, Optional, Regexp, ValidationError,
)
from wtforms.widgets import NumberInput

EDAD_MAXIMA_MESES = 60  # RespiraKids está dirigido a menores de 5 años

OBLIGATORIO = 'Este campo es obligatorio.'
MENSAJE_PASSWORD = 'La contraseña debe tener al menos 8 caracteres e incluir letras y números.'

_PATRON_NOMBRE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[ '\-][A-Za-zÀ-ÖØ-öø-ÿ]+)*$")
_PATRON_TELEFONO = re.compile(r'^\+?[0-9 ()\-]+$')
_PATRON_CORREO = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
MENSAJE_CORREO = 'Escribe un correo válido, por ejemplo nombre@correo.com.'


# ---------------------------------------------------------------- Filtros (normalización)

def limpiar_espacios(valor):
    return ' '.join(valor.split()) if isinstance(valor, str) else valor


def minusculas(valor):
    return valor.lower() if isinstance(valor, str) else valor


def recortar(valor):
    return valor.strip() if isinstance(valor, str) else valor


# ---------------------------------------------------------------- Validadores reutilizables

def nombre_persona(form, field):
    if field.data and not _PATRON_NOMBRE.match(field.data):
        raise ValidationError('Usa solo letras, espacios, guiones o apóstrofos.')


def telefono_valido(form, field):
    if not field.data:
        return
    digitos = sum(c.isdigit() for c in field.data)
    if not _PATRON_TELEFONO.match(field.data) or not 7 <= digitos <= 15:
        raise ValidationError('Escribe un teléfono válido (entre 7 y 15 dígitos).')


def password_segura(form, field):
    valor = field.data or ''
    if len(valor) < 8 or not any(c.isalpha() for c in valor) or not any(c.isdigit() for c in valor):
        raise ValidationError(MENSAJE_PASSWORD)


def fecha_no_futura(form, field):
    if field.data and field.data > date.today():
        raise ValidationError('La fecha no puede ser posterior a hoy.')


def primer_error(form):
    """Primer mensaje de error del formulario, para formularios que responden con flash()."""
    for errores in form.errors.values():
        if errores:
            return errores[0]
    return 'Revisa los datos del formulario.'


# ---------------------------------------------------------------- Fábricas de campos comunes

def _campo_nombre_persona(etiqueta, autocomplete, requerido):
    return StringField(
        etiqueta,
        filters=[limpiar_espacios],
        validators=[
            DataRequired(OBLIGATORIO) if requerido else Optional(),
            Length(min=2, max=100, message='Debe tener entre 2 y 100 caracteres.'),
            nombre_persona,
        ],
        render_kw={'maxlength': 100, 'autocomplete': autocomplete},
    )


def campo_nombres(etiqueta='Nombres', requerido=True):
    return _campo_nombre_persona(etiqueta, 'given-name', requerido)


def campo_apellidos(etiqueta='Apellidos', requerido=True):
    return _campo_nombre_persona(etiqueta, 'family-name', requerido)


def correo_con_formato(form, field):
    """Formato básico de correo. Para buscar cuentas existentes (login, autorizaciones) no se
    aplican las reglas de dominio de registro, que rechazan dominios reservados como .test."""
    if field.data and not _PATRON_CORREO.match(field.data):
        raise ValidationError(MENSAJE_CORREO)


def campo_correo(etiqueta='Correo electrónico', para_registro=False):
    validador = Email(message=MENSAJE_CORREO) if para_registro else correo_con_formato
    return EmailField(
        etiqueta,
        filters=[limpiar_espacios, minusculas],
        validators=[DataRequired(OBLIGATORIO), validador, Length(max=120)],
        render_kw={'maxlength': 120, 'autocomplete': 'email', 'placeholder': 'nombre@correo.com'},
    )


def campo_telefono(etiqueta='Teléfono celular'):
    return TelField(
        etiqueta,
        filters=[limpiar_espacios],
        validators=[Optional(), Length(max=30), telefono_valido],
        render_kw={'maxlength': 30, 'autocomplete': 'tel', 'placeholder': '300 000 0000', 'inputmode': 'tel'},
    )


def campo_password_nueva(etiqueta='Contraseña'):
    return PasswordField(
        etiqueta,
        validators=[DataRequired(OBLIGATORIO), Length(max=128), password_segura],
        description='Mínimo 8 caracteres, con letras y números.',
        render_kw={'minlength': 8, 'maxlength': 128, 'autocomplete': 'new-password'},
    )


def campo_confirmar_password(referencia, etiqueta='Confirmar contraseña'):
    return PasswordField(
        etiqueta,
        validators=[DataRequired(OBLIGATORIO), EqualTo(referencia, message='Las contraseñas no coinciden.')],
        render_kw={'maxlength': 128, 'autocomplete': 'new-password'},
    )


# ---------------------------------------------------------------- Autenticación y cuenta

class LoginForm(FlaskForm):
    correo = campo_correo()
    password = PasswordField(
        'Contraseña', validators=[DataRequired(OBLIGATORIO), Length(max=128)],
        render_kw={'maxlength': 128, 'autocomplete': 'current-password'},
    )


class RegistroForm(FlaskForm):
    nombre = campo_nombres()
    apellido = campo_apellidos()
    correo = campo_correo(para_registro=True)
    telefono = campo_telefono()
    password = campo_password_nueva()
    confirmar_password = campo_confirmar_password('password')
    acepta_politica = BooleanField(
        'Acepto la política de tratamiento de datos personales',
        validators=[DataRequired('Debes aceptar la política de tratamiento de datos para crear la cuenta.')],
    )


class AceptarPoliticaForm(FlaskForm):
    acepta_politica = BooleanField(
        'Acepto la política de tratamiento de datos personales',
        validators=[DataRequired('Debes aceptar la política de tratamiento de datos para continuar.')],
    )


class PerfilCuidadorForm(FlaskForm):
    nombre = campo_nombres()
    apellido = campo_apellidos()
    telefono = campo_telefono()


class PerfilProfesionalForm(FlaskForm):
    nombre = campo_nombres()
    apellido = campo_apellidos()
    especialidad = StringField(
        'Especialidad', filters=[limpiar_espacios], validators=[Optional(), Length(max=100)],
        render_kw={'maxlength': 100},
    )
    numero_licencia = StringField(
        'Número de registro profesional', filters=[limpiar_espacios], validators=[Optional(), Length(max=50)],
        render_kw={'maxlength': 50},
    )


class CambioPasswordForm(FlaskForm):
    password_actual = PasswordField(
        'Contraseña actual', validators=[DataRequired(OBLIGATORIO)],
        render_kw={'autocomplete': 'current-password'},
    )
    password_nueva = campo_password_nueva('Nueva contraseña')
    password_confirmar = campo_confirmar_password('password_nueva', 'Confirmar nueva contraseña')


# ---------------------------------------------------------------- Niños

class NinoForm(FlaskForm):
    nombre = campo_nombres()
    apellido = campo_apellidos()
    fecha_nacimiento = DateField(
        'Fecha de nacimiento', validators=[DataRequired('Indica la fecha de nacimiento.'), fecha_no_futura],
    )
    sexo = SelectField(
        'Sexo', choices=[('', 'Selecciona…'), ('F', 'Femenino'), ('M', 'Masculino')],
        validators=[DataRequired('Selecciona el sexo.')],
    )
    peso_kg = FloatField(
        'Peso (kg)',
        validators=[Optional(), NumberRange(min=0.3, max=40, message='El peso debe estar entre 0,3 y 40 kg.')],
        widget=NumberInput(step='0.1', min=0.3, max=40),
    )
    talla_cm = FloatField(
        'Talla (cm)',
        validators=[Optional(), NumberRange(min=20, max=130, message='La talla debe estar entre 20 y 130 cm.')],
        widget=NumberInput(step='0.1', min=20, max=130),
    )
    # Solo se exige al registrar; después se gestiona en la página de consentimiento.
    consentimiento_tratamiento = BooleanField('Autorizo el tratamiento de datos de salud')
    consentimiento_investigacion = BooleanField('Autorizo el uso anonimizado para investigación')

    def __init__(self, *args, es_nuevo=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.es_nuevo = es_nuevo
        # Refleja en la interfaz (asterisco) que la autorización es obligatoria al registrar.
        self.consentimiento_tratamiento.flags.required = es_nuevo

    def validate_fecha_nacimiento(self, field):
        hoy = date.today()
        meses = (hoy.year - field.data.year) * 12 + (hoy.month - field.data.month) - (hoy.day < field.data.day)
        if self.es_nuevo and meses >= EDAD_MAXIMA_MESES:
            raise ValidationError('RespiraKids está dirigido a niños y niñas menores de 5 años.')

    def validate_consentimiento_tratamiento(self, field):
        if self.es_nuevo and not field.data:
            raise ValidationError('Para registrar al niño/a debes autorizar el tratamiento de sus datos de salud.')


class ConsentimientoNinoForm(FlaskForm):
    consentimiento_tratamiento = BooleanField('Autorizo el tratamiento de datos de salud')
    consentimiento_investigacion = BooleanField('Autorizo el uso anonimizado para investigación')


class PatologiaForm(FlaskForm):
    nombre = StringField(
        'Condición o patología', filters=[limpiar_espacios],
        validators=[DataRequired('Indica el nombre de la condición o patología.'), Length(max=150)],
        render_kw={'maxlength': 150, 'placeholder': 'Ej. Asma, rinitis alérgica'},
    )
    fecha_diagnostico = DateField('Fecha de diagnóstico', validators=[Optional(), fecha_no_futura])
    descripcion = TextAreaField(
        'Notas', filters=[recortar], validators=[Optional(), Length(max=2000)],
        render_kw={'maxlength': 2000, 'rows': 2},
    )


class AutorizacionForm(FlaskForm):
    correo_profesional = campo_correo('Correo del profesional')


class MensajeForm(FlaskForm):
    contenido = TextAreaField(
        'Mensaje', filters=[recortar],
        validators=[DataRequired('Escribe un mensaje.'), Length(max=2000)], render_kw={'maxlength': 2000},
    )


class SolicitudDerechosForm(FlaskForm):
    tipo = SelectField('Tipo de solicitud', choices=[], validators=[DataRequired('Selecciona el tipo de solicitud.')])
    nino_id = SelectField('Se refiere a', choices=[], coerce=int, validators=[InputRequired(OBLIGATORIO)])
    descripcion = TextAreaField(
        'Descripción', filters=[recortar],
        validators=[DataRequired('Describe tu solicitud.'),
                    Length(min=10, max=2000, message='Escribe entre 10 y 2000 caracteres.')],
        render_kw={'minlength': 10, 'maxlength': 2000, 'rows': 3, 'placeholder': 'Cuéntanos qué necesitas'},
    )

    def __init__(self, *args, ninos=(), **kwargs):
        super().__init__(*args, **kwargs)
        from app.models.privacidad import TIPOS_SOLICITUD
        self.tipo.choices = [('', 'Selecciona…')] + list(TIPOS_SOLICITUD.items())
        self.nino_id.choices = (
            [(0, 'Mi cuenta (no se refiere a un niño/a)')] + [(n.id, n.nombre_completo) for n in ninos]
        )


# ---------------------------------------------------------------- Síntomas

def _signo(etiqueta, ayuda=None):
    return BooleanField(etiqueta, description=ayuda)


def _entero(etiqueta, minimo, maximo, ayuda=None, unidad=''):
    return IntegerField(
        etiqueta, description=ayuda,
        validators=[Optional(), NumberRange(min=minimo, max=maximo,
                                            message=f'Debe estar entre {minimo} y {maximo}{unidad}.')],
        widget=NumberInput(min=minimo, max=maximo),
    )


class SintomasForm(FlaskForm):
    """Registro de síntomas y signos. Los criterios que usa el motor clínico están en app/clinica/reglas_v1.py.

    Ningún campo es obligatorio: el cuidador responde lo que observó. GRUPOS define el orden de las
    preguntas: primero los signos de alarma.
    """
    # Signos de alarma (Herramienta Clínica, Módulos 5 y 6)
    incapacidad_beber_liquidos = _signo('No puede beber ni tragar líquidos', 'Rechaza o no logra tomar líquidos ni el pecho.')
    convulsion = _signo('Ha tenido una convulsión', 'Movimientos involuntarios del cuerpo, rigidez o temblores sin control.')
    alteracion_conciencia = _signo('Está muy somnoliento/a o es difícil despertarlo/a', 'No responde como siempre.')
    cianosis = _signo('Labios o piel de color azulado')
    tiraje_subcostal = _signo('Se le hunde la piel debajo de las costillas al respirar', 'Se conoce como tiraje subcostal.')
    quejido = _signo('Hace un quejido al respirar', 'Un sonido corto, como un gemido, al sacar el aire.')
    aleteo_nasal = _signo('Se le abren y cierran las aletas de la nariz al respirar')
    apnea = _signo('Hace pausas en la respiración', 'Deja de respirar por unos segundos.')
    estridor = _signo('Hace un ruido agudo al tomar aire estando tranquilo/a', 'Estridor en reposo, no solo al llorar.')
    rigidez_cuello = _signo('Tiene el cuello rígido', 'No puede bajar la barbilla hacia el pecho.')
    abombamiento_fontanela = _signo('La fontanela o mollera está abombada o levantada', 'Solo en bebés que aún la tienen abierta.')
    petequias = _signo('Tiene manchas rojas o moradas en la piel', 'Puntos o manchas que no desaparecen al presionarlas.')
    edema_retroauricular = _signo('Tiene hinchazón y enrojecimiento detrás de la oreja')

    # Respiración
    dificultad_respiratoria = _signo('Le cuesta respirar')
    respiracion_rapida = _signo('Respira más rápido de lo normal', 'Si puedes, cuenta las respiraciones en 1 minuto.')
    sibilancias = _signo('Se le escucha un silbido en el pecho al respirar', 'Se conoce como sibilancias.')
    frecuencia_respiratoria = _entero(
        'Respiraciones en 1 minuto', 5, 150, unidad=' respiraciones',
        ayuda='Cuéntalas durante 1 minuto completo, con el niño/a despierto/a y sin llorar.')
    spo2 = _entero('Saturación de oxígeno (%)', 50, 100, unidad=' %', ayuda='Solo si tienes un oxímetro.')
    altitud_msnm = _entero('Altitud del lugar donde está (metros sobre el nivel del mar)', 0, 5000,
                           ayuda='Necesaria para interpretar la saturación de oxígeno. Ej.: Bogotá 2600, Medellín 1500.')

    # Tos y fiebre
    tos = _signo('Tiene tos')
    dias_tos = _entero('¿Cuántos días lleva con tos?', 0, 180, unidad=' días')
    tos_paroxistica = _signo('Tiene accesos de tos', 'Muchas toses seguidas, sin poder tomar aire entre ellas.')
    vomito_tras_tos = _signo('Vomita después de los accesos de tos')
    temperatura = DecimalField('Temperatura (°C)', places=1, validators=[
        Optional(), NumberRange(min=34, max=43, message='La temperatura debe estar entre 34 y 43 °C.'),
    ], widget=NumberInput(step='0.1', min=34, max=43))
    dias_fiebre = _entero('¿Cuántos días lleva con fiebre?', 0, 60, unidad=' días')

    # Otros síntomas
    congestion_nasal = _signo('Nariz tapada')
    secrecion_nasal = _signo('Secreción o moco nasal')
    estornudos = _signo('Estornudos')
    dolor_garganta = _signo('Dolor de garganta')
    decaimiento = _signo('Decaimiento')
    disminucion_actividad = _signo('Juega o se mueve menos de lo habitual')
    perdida_apetito = _signo('Pérdida de apetito')
    perdida_peso = _signo('Ha perdido peso o no está ganando peso')
    irritabilidad = _signo('Irritabilidad')
    vomito = _signo('Vómito')
    diarrea = _signo('Diarrea')

    # Antecedentes y contexto
    contacto_tuberculosis = _signo('Convive o tiene contacto cercano con alguien con tuberculosis')
    factor_riesgo_bar = _signo(
        'Tiene alguna de estas condiciones',
        'Nació prematuro con menos de 2000 g (si tiene menos de 6 meses), enfermedad del corazón congénita, '
        'displasia broncopulmonar, fibrosis quística, inmunodeficiencia, trasplante, enfermedad neurológica moderada '
        'o grave, síndrome de Down o desnutrición aguda grave.')
    condicion_asma = _signo('Tiene diagnóstico de asma')
    condicion_alergias = _signo('Tiene alergias respiratorias')
    observaciones = TextAreaField('Notas adicionales', filters=[recortar], validators=[Optional(), Length(max=1000)],
                                  render_kw={'maxlength': 1000, 'rows': 3})

    GRUPOS = (
        ('alarma', 'Signos de alarma', 'Marca si observas alguno de estos signos ahora mismo.', (
            'incapacidad_beber_liquidos', 'convulsion', 'alteracion_conciencia', 'cianosis', 'tiraje_subcostal',
            'quejido', 'aleteo_nasal', 'apnea', 'estridor', 'rigidez_cuello', 'abombamiento_fontanela', 'petequias',
            'edema_retroauricular')),
        ('respiracion', 'Respiración', None, (
            'dificultad_respiratoria', 'respiracion_rapida', 'sibilancias', 'frecuencia_respiratoria', 'spo2',
            'altitud_msnm')),
        ('tos_fiebre', 'Tos y fiebre', None, (
            'tos', 'dias_tos', 'tos_paroxistica', 'vomito_tras_tos', 'temperatura', 'dias_fiebre')),
        ('otros', 'Otros síntomas', None, (
            'congestion_nasal', 'secrecion_nasal', 'estornudos', 'dolor_garganta', 'decaimiento',
            'disminucion_actividad', 'perdida_apetito', 'perdida_peso', 'irritabilidad', 'vomito', 'diarrea')),
        ('antecedentes', 'Antecedentes y contexto', None, (
            'contacto_tuberculosis', 'factor_riesgo_bar', 'condicion_asma', 'condicion_alergias', 'observaciones')),
    )

    def validate_dias_tos(self, field):
        if field.data and not self.tos.data:
            raise ValidationError('Indicaste días de tos: marca también "Tiene tos".')

    def validate_tos_paroxistica(self, field):
        if field.data and not self.tos.data:
            raise ValidationError('Los accesos de tos requieren marcar también "Tiene tos".')

    def validate_spo2(self, field):
        if field.data is not None and self.altitud_msnm.data is None:
            raise ValidationError('Indica la altitud del lugar para poder interpretar la saturación.')

    def datos_registro(self):
        """Diccionario listo para construir un RegistroSintomas."""
        datos = {}
        for _, _, _, campos in self.GRUPOS:
            for nombre in campos:
                datos[nombre] = getattr(self, nombre).data
        datos['temperatura'] = float(datos['temperatura']) if datos['temperatura'] is not None else None
        datos['spo2'] = float(datos['spo2']) if datos['spo2'] is not None else None
        datos['observaciones'] = datos['observaciones'] or None
        return datos


# ---------------------------------------------------------------- Medicamentos (registrados por un profesional)

class MedicamentoForm(Form):
    """Un medicamento dentro de una receta. Subformulario: el token CSRF lo aporta RecetaForm."""
    nombre = StringField('Medicamento', filters=[limpiar_espacios],
                         validators=[DataRequired(OBLIGATORIO), Length(max=150)], render_kw={'maxlength': 150})
    dosis = StringField('Dosis', filters=[limpiar_espacios], description='Tal como debe administrarse. Ej.: 5 ml.',
                        validators=[DataRequired(OBLIGATORIO), Length(max=100)], render_kw={'maxlength': 100})
    frecuencia_horas = IntegerField(
        'Cada cuántas horas', validators=[DataRequired(OBLIGATORIO), NumberRange(min=1, max=48, message='Entre 1 y 48 horas.')],
        widget=NumberInput(min=1, max=48))
    duracion_dias = IntegerField(
        'Durante cuántos días', description='Si lo indicas, se programan los recordatorios de cada toma.',
        validators=[Optional(), NumberRange(min=1, max=90, message='Entre 1 y 90 días.')], widget=NumberInput(min=1, max=90))
    instrucciones = TextAreaField('Instrucciones', filters=[recortar], validators=[Optional(), Length(max=500)],
                                  render_kw={'maxlength': 500, 'rows': 2})

    def datos(self):
        return {'nombre': self.nombre.data, 'dosis': self.dosis.data, 'frecuencia_horas': self.frecuencia_horas.data,
                'duracion_dias': self.duracion_dias.data, 'instrucciones': self.instrucciones.data or None}


class RecetaForm(FlaskForm):
    motivo = StringField('Motivo', filters=[limpiar_espacios],
                         validators=[DataRequired(OBLIGATORIO), Length(max=255)], render_kw={'maxlength': 255})
    indicaciones_generales = TextAreaField('Indicaciones generales', filters=[recortar],
                                           validators=[Optional(), Length(max=2000)],
                                           render_kw={'maxlength': 2000, 'rows': 3})
    fecha_inicio = DateTimeLocalField('Inicio del tratamiento', format='%Y-%m-%dT%H:%M',
                                      validators=[DataRequired('Indica la fecha y hora de inicio.')])
    medicamentos = FieldList(FormField(MedicamentoForm), label='Medicamento', min_entries=1, max_entries=5)


# ---------------------------------------------------------------- Administración

TIPOS_DOCUMENTO = [('', 'Selecciona…'), ('CC', 'Cédula de ciudadanía'), ('CE', 'Cédula de extranjería'),
                   ('PA', 'Pasaporte'), ('PPT', 'Permiso por protección temporal')]


class ProfesionalAdminForm(FlaskForm):
    """Alta de un profesional de salud por parte del administrador."""
    nombre = campo_nombres()
    apellido = campo_apellidos()
    correo = campo_correo(para_registro=True)
    telefono = campo_telefono()
    tipo_documento = SelectField('Tipo de documento', choices=TIPOS_DOCUMENTO,
                                 validators=[DataRequired('Selecciona el tipo de documento.')])
    numero_documento = StringField(
        'Número de documento', filters=[limpiar_espacios],
        validators=[DataRequired(OBLIGATORIO), Length(min=4, max=30),
                    Regexp(r'^[A-Za-z0-9\-]+$', message='Usa solo letras, números o guiones.')],
        render_kw={'maxlength': 30, 'autocomplete': 'off'})
    profesion = StringField('Profesión', filters=[limpiar_espacios],
                            validators=[DataRequired(OBLIGATORIO), Length(max=100)],
                            render_kw={'maxlength': 100, 'placeholder': 'Ej. Medicina, Enfermería'})
    especialidad = StringField('Especialidad', filters=[limpiar_espacios], validators=[Optional(), Length(max=100)],
                               render_kw={'maxlength': 100})
    tarjeta_profesional = StringField('Tarjeta o registro profesional', filters=[limpiar_espacios],
                                      validators=[DataRequired(OBLIGATORIO), Length(max=50)], render_kw={'maxlength': 50})
    registro_rethus = StringField('Registro en ReTHUS', filters=[limpiar_espacios],
                                  description='Registro Único Nacional del Talento Humano en Salud.',
                                  validators=[Optional(), Length(max=50)], render_kw={'maxlength': 50})


class ResponderSolicitudForm(FlaskForm):
    estado = SelectField('Estado', choices=[('en_tramite', 'En trámite'), ('resuelta', 'Resuelta'),
                                            ('rechazada', 'Rechazada')],
                         validators=[DataRequired(OBLIGATORIO)])
    respuesta = TextAreaField('Respuesta al titular', filters=[recortar],
                              description='Obligatoria al resolver o rechazar. El titular la verá en "Mis datos".',
                              validators=[Optional(), Length(max=2000)], render_kw={'maxlength': 2000, 'rows': 4})

    def validate(self, extra_validators=None):
        # Se valida aquí y no con validate_respuesta: Optional() corta la cadena cuando el campo está vacío.
        valido = super().validate(extra_validators)
        if self.estado.data in ('resuelta', 'rechazada') and len(self.respuesta.data or '') < 10:
            self.respuesta.errors = list(self.respuesta.errors) + [
                'Escribe una respuesta de al menos 10 caracteres para el titular.']
            return False
        return valido

# ---------------------------------------------------------------- Apoyo a los templates

def atributos_campo(field, extra=None, clase=None):
    """Atributos HTML de accesibilidad y estado de error para dibujar un campo (usado por las macros)."""
    atributos = dict(extra or {})
    descripciones = []
    if field.description:
        descripciones.append(f'{field.id}-ayuda')
    if field.errors:
        descripciones.append(f'{field.id}-error')
        atributos['aria-invalid'] = 'true'
    if descripciones:
        atributos['aria-describedby'] = ' '.join(descripciones)
    if clase:
        atributos['class'] = clase + (' is-invalid' if field.errors else '')
    return atributos
