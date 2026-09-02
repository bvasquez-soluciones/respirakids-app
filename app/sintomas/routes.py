from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.sintomas import sintomas_bp
from app.decorators import rol_requerido
from app.models import Nino, RegistroSintomas, Evaluacion
from app.semaforo import clasificar_riesgo
from app.ml_model import predecir_riesgo_ml
from app import db


def verificar_acceso_nino(nino):
    """Verifica que el niño pertenezca al cuidador actual."""
    if nino.cuidador_id != current_user.id:
        abort(403)


@sintomas_bp.route('/nino/<int:nino_id>')
@login_required
@rol_requerido('cuidador', 'admin')
def listar(nino_id):
    nino = Nino.query.get_or_404(nino_id)
    verificar_acceso_nino(nino)

    registros = RegistroSintomas.query.filter_by(nino_id=nino.id).order_by(RegistroSintomas.fecha.desc()).all()
    return render_template('sintomas/listar.html', nino=nino, registros=registros)


@sintomas_bp.route('/nino/<int:nino_id>/nuevo', methods=['GET', 'POST'])
@login_required
@rol_requerido('cuidador', 'admin')
def nuevo(nino_id):
    nino = Nino.query.get_or_404(nino_id)
    verificar_acceso_nino(nino)

    if request.method == 'POST':
        registro = RegistroSintomas(
            nino_id=nino.id,
            temperatura=request.form.get('temperatura') or None,
            tos='tos' in request.form,
            dificultad_respiratoria='dificultad_respiratoria' in request.form,
            respiracion_rapida='respiracion_rapida' in request.form,
            congestion_nasal='congestion_nasal' in request.form,
            secrecion_nasal='secrecion_nasal' in request.form,
            dolor_garganta='dolor_garganta' in request.form,
            decaimiento='decaimiento' in request.form,
            perdida_apetito='perdida_apetito' in request.form,
            vomito='vomito' in request.form,
            diarrea='diarrea' in request.form,
            estornudos='estornudos' in request.form,
            irritabilidad='irritabilidad' in request.form,
            severidad=request.form.get('severidad') or None,
            inicio_sintomas=request.form.get('inicio_sintomas') or None,
            condicion_asma='condicion_asma' in request.form,
            condicion_alergias='condicion_alergias' in request.form,
            otros_sintomas=request.form.get('otros_sintomas'),
            observaciones=request.form.get('observaciones'),
        )

        db.session.add(registro)
        db.session.commit()

        # Clasificación por reglas de semáforo y predicción por ML
        nivel, motivo, recomendaciones = clasificar_riesgo(registro)
        ml_nivel, ml_confianza = predecir_riesgo_ml(registro, nino)

        evaluacion = Evaluacion(
            nino_id=nino.id,
            registro_sintomas_id=registro.id,
            nivel_riesgo=nivel,
            motivo=motivo,
            recomendaciones=recomendaciones,
            ml_nivel_riesgo=ml_nivel,
            ml_confianza=ml_confianza
        )
        db.session.add(evaluacion)
        db.session.commit()

        flash('Síntomas registrados correctamente.', 'success')
        return redirect(url_for('sintomas.resultado', evaluacion_id=evaluacion.id))

    return render_template('sintomas/nuevo.html', nino=nino)


@sintomas_bp.route('/resultado/<int:evaluacion_id>')
@login_required
@rol_requerido('cuidador', 'admin')
def resultado(evaluacion_id):
    evaluacion = Evaluacion.query.get_or_404(evaluacion_id)
    verificar_acceso_nino(evaluacion.nino)

    return render_template('sintomas/resultado.html', evaluacion=evaluacion)