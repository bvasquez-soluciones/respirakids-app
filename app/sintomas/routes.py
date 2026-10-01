from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app import db
from app.decorators import rol_requerido
from app.forms import SintomasForm
from app.ml.prediccion import predecir
from app.models import Evaluacion, RegistroSintomas
from app.clinica.motor import evaluar
from app.presentacion import datos_complementarios, hallazgos_registrados
from app.services.acceso import nino_del_cuidador
from app.services.auditoria import registrar_actividad
from app.services.resumen_nino import avisos_de_evaluacion, datos_evolucion, senales_de_evaluacion
from app.sintomas import sintomas_bp

ROLES_CUIDADOR = ('cuidador', 'admin')


@sintomas_bp.route('/nino/<int:nino_id>')
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def listar(nino_id):
    nino = nino_del_cuidador(nino_id)
    registros = (
        RegistroSintomas.query.filter_by(nino_id=nino.id)
        .order_by(RegistroSintomas.fecha.desc(), RegistroSintomas.id.desc())
        .all()
    )
    registrar_actividad('consultar_historial', 'nino', nino.id)
    return render_template('sintomas/listar.html', nino=nino, registros=registros,
                           evolucion=datos_evolucion(registros))


@sintomas_bp.route('/nino/<int:nino_id>/nuevo', methods=['GET', 'POST'])
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def nuevo(nino_id):
    nino = nino_del_cuidador(nino_id, solo_activos=True)
    if not nino.consentimiento_otorgado:
        flash('Antes de registrar síntomas debes autorizar el tratamiento de los datos de salud de '
              f'{nino.nombre}.', 'warning')
        return redirect(url_for('pacientes.consentimiento', nino_id=nino.id))
    form = SintomasForm()

    if request.method == 'POST':
        if not form.validate_on_submit():
            return render_template('sintomas/nuevo.html', nino=nino, form=form), 400

        registro = RegistroSintomas(nino_id=nino.id, **form.datos_registro())
        db.session.add(registro)
        db.session.flush()  # asigna id y fecha sin cerrar la transacción

        # Clasificación clínica por reglas (determinante) y predicción ML (complementaria).
        resultado = evaluar(registro, nino)
        prediccion = predecir(registro, nino)

        evaluacion = Evaluacion(
            nino_id=nino.id,
            registro_sintomas_id=registro.id,
            nivel_riesgo=resultado.nivel,
            motivo=resultado.motivo,
            recomendaciones=resultado.recomendaciones,
            version_reglas=resultado.version,
            senales_json=resultado.detalle_json(),
            ml_nivel_riesgo=prediccion.nivel if prediccion else None,
            ml_confianza=prediccion.confianza if prediccion else None,
            ml_version=prediccion.version if prediccion else None,
        )
        db.session.add(evaluacion)
        db.session.commit()  # registro y evaluación se guardan juntos o no se guarda nada
        registrar_actividad('crear_evaluacion', 'nino', nino.id, detalles={
            'registro_id': registro.id, 'evaluacion_id': evaluacion.id,
            'nivel': resultado.nivel, 'version_reglas': resultado.version,
            'reglas': [s['regla_id'] for s in resultado.senales],
        })

        flash('Síntomas registrados correctamente.', 'success')
        return redirect(url_for('sintomas.resultado', evaluacion_id=evaluacion.id))

    return render_template('sintomas/nuevo.html', nino=nino, form=form)


@sintomas_bp.route('/resultado/<int:evaluacion_id>')
@login_required
@rol_requerido(*ROLES_CUIDADOR)
def resultado(evaluacion_id):
    evaluacion = db.session.get(Evaluacion, evaluacion_id)
    if evaluacion is None:
        abort(404)
    nino_del_cuidador(evaluacion.nino_id)
    registrar_actividad('consultar_evaluacion', 'evaluacion', evaluacion.id)
    registro = evaluacion.registro_sintomas
    return render_template(
        'sintomas/resultado.html', evaluacion=evaluacion, registro=registro,
        senales=senales_de_evaluacion(evaluacion), avisos=avisos_de_evaluacion(evaluacion),
        hallazgos=hallazgos_registrados(registro),
        complementarios=datos_complementarios(registro),
    )
