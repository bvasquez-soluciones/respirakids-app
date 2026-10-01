"""Comandos del modelo ML complementario.

    flask ml generar-dataset   -> ml/datos/dataset_sintetico_v1.csv
    flask ml entrenar          -> app/ml_models/riesgo_v1.joblib (+ .json) y ml/MODELO_ML.md
"""
import os

import click
import pandas as pd
from flask import current_app
from flask.cli import AppGroup

from app.ml.entrenamiento import ficha_markdown, entrenar, generar_dataset, guardar

RUTA_FICHA = os.path.join('ml', 'MODELO_ML.md')

ml_cli = AppGroup('ml', help='Modelo de Machine Learning complementario (datos sintéticos).')


@ml_cli.command('generar-dataset')
@click.option('--filas', default=6000, show_default=True)
@click.option('--semilla', default=2026, show_default=True)
def generar(filas, semilla):
    """Genera el dataset SINTÉTICO etiquetado con las reglas clínicas vigentes."""
    ruta = current_app.config['ML_RUTA_DATASET']
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    df = generar_dataset(filas, semilla)
    df.to_csv(ruta, index=False)
    click.echo(f'Dataset sintético: {len(df)} filas -> {ruta}')
    click.echo(df['nivel'].value_counts().to_string())


@ml_cli.command('entrenar')
@click.option('--semilla', default=2026, show_default=True)
def entrenar_modelo(semilla):
    """Entrena el modelo, guarda sus metadatos con hash de integridad y genera la ficha del modelo."""
    ruta_dataset = current_app.config['ML_RUTA_DATASET']
    if not os.path.exists(ruta_dataset):
        raise click.ClickException('No existe el dataset. Ejecuta primero: flask ml generar-dataset')
    df = pd.read_csv(ruta_dataset)
    modelo, metadatos = entrenar(df, semilla)
    metadatos = guardar(modelo, metadatos, current_app.config['ML_RUTA_MODELO'], ruta_dataset)
    with open(RUTA_FICHA, 'w', encoding='utf-8', newline='\n') as archivo:
        archivo.write(ficha_markdown(metadatos))
    metricas = metadatos['metricas_prueba']
    click.echo(f'Modelo {metadatos["version"]} guardado. Exactitud {metricas["exactitud"]}, '
               f'F1 macro {metricas["f1_macro"]}, rojos predichos como verde: {metricas["rojos_predichos_como_verde"]}.')
    click.echo(f'Ficha del modelo: {RUTA_FICHA}')
