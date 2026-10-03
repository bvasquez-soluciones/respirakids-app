"""Modelos de datos de RespiraKids, organizados por dominio."""
from app.models.base import ahora_utc
from app.models.identidad import Cuidador, Profesional
from app.models.ninos import Nino, PatologiaBase, Autorizacion, SeguimientoEvolucion
from app.models.clinica import RegistroSintomas, Evaluacion, NIVELES_RIESGO
from app.models.comunicacion import (
    AdjuntoMensaje, Mensaje, Notificacion, SenalVideollamada, SolicitudAtencion, Videollamada,
)
from app.models.medicacion import Receta, MedicamentoRecetado, TomaMedicamento
from app.models.conocimiento import FuenteConocimiento, ConocimientoSanitario, ConsultaIA
from app.models.auditoria import LogSeguridad, LogActividad, VersionRegistro
from app.models.privacidad import Consentimiento, SolicitudDerechos

__all__ = [
    'ahora_utc',
    'Cuidador', 'Profesional',
    'Nino', 'PatologiaBase', 'Autorizacion', 'SeguimientoEvolucion',
    'RegistroSintomas', 'Evaluacion', 'NIVELES_RIESGO',
    'Mensaje', 'Notificacion', 'SolicitudAtencion', 'AdjuntoMensaje', 'Videollamada', 'SenalVideollamada',
    'Receta', 'MedicamentoRecetado', 'TomaMedicamento',
    'FuenteConocimiento', 'ConocimientoSanitario', 'ConsultaIA',
    'LogSeguridad', 'LogActividad', 'VersionRegistro',
    'Consentimiento', 'SolicitudDerechos',
]
