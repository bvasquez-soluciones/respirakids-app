"""Generación del dataset sintético, entrenamiento y ficha del modelo ML complementario.

Las variables del modelo son exactamente las del motor clínico (`DatosEvaluacion`), para que el modelo y
las reglas describan al niño/a con los mismos datos.
"""
import hashlib
import json
import os
import platform
from dataclasses import fields
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, recall_score
from sklearn.model_selection import train_test_split

from app.clinica.motor import DatosEvaluacion, evaluar_v1
from app.clinica.reglas_v1 import VERSION as VERSION_REGLAS

VERSION_MODELO = 'ml-v1-sintetico'
CLASES = ('verde', 'amarillo', 'rojo')
VARIABLES = tuple(f.name for f in fields(DatosEvaluacion))
VARIABLES_NUMERICAS = tuple(f.name for f in fields(DatosEvaluacion) if f.type is not bool)

LIMITACIONES = (
    'Entrenado con datos SINTÉTICOS (generados por programa), no con casos reales.',
    f'Las etiquetas las asignan las reglas clínicas {VERSION_REGLAS}: el modelo aprende a imitarlas y hereda '
    'sus limitaciones, incluida su validación clínica pendiente.',
    'Las proporciones de cada síntoma en el dataset son supuestos del generador, no epidemiología real.',
    'Una exactitud alta solo indica que imita bien las reglas; no indica capacidad de predecir riesgo real.',
    'No es un dispositivo médico ni una herramienta validada: su resultado no debe usarse para decisiones clínicas.',
    'Para un uso real debe reentrenarse con datos reales anonimizados, etiquetados por profesionales y '
    'evaluarse de forma independiente.',
)

# Supuestos del generador (probabilidad de que aparezca cada signo). Son arbitrarios y están documentados.
PROBABILIDADES = {
    'tos': 0.60, 'congestion_nasal': 0.50, 'secrecion_nasal': 0.45, 'estornudos': 0.30, 'dolor_garganta': 0.15,
    'dificultad_respiratoria': 0.12, 'respiracion_rapida': 0.12, 'sibilancias': 0.12,
    'tiraje_subcostal': 0.03, 'cianosis': 0.02, 'incapacidad_beber_liquidos': 0.03, 'aleteo_nasal': 0.02,
    'quejido': 0.02, 'apnea': 0.015, 'convulsion': 0.015, 'alteracion_conciencia': 0.015, 'estridor': 0.03,
    'rigidez_cuello': 0.01, 'abombamiento_fontanela': 0.01, 'petequias': 0.01, 'edema_retroauricular': 0.01,
    'contacto_tuberculosis': 0.02, 'perdida_peso': 0.04, 'disminucion_actividad': 0.08, 'factor_riesgo_bar': 0.05,
}


def _fila_sintetica(rng):
    edad = int(rng.integers(0, 60))
    fila = {campo: bool(rng.random() < p) for campo, p in PROBABILIDADES.items()}
    fila['tos_paroxistica'] = fila['tos'] and rng.random() < 0.12
    fila['vomito_tras_tos'] = fila['tos'] and rng.random() < 0.06
    fila['edad_meses'] = edad
    fila['temperatura'] = round(float(np.clip(rng.normal(38.0, 0.9), 35.5, 41.5)), 1) if rng.random() < 0.55 else None
    base_fr = 45 if edad < 2 else (38 if edad < 12 else 30)
    fila['frecuencia_respiratoria'] = (int(np.clip(rng.normal(base_fr, 11), 15, 90))
                                       if rng.random() < 0.45 else None)
    if rng.random() < 0.15:
        fila['altitud_msnm'] = int(rng.choice([0, 800, 1500, 1800, 2600, 3200]))
        fila['spo2'] = float(int(np.clip(rng.normal(94, 3.5), 70, 100)))
    else:
        fila['altitud_msnm'] = None
        fila['spo2'] = None
    fila['dias_tos'] = int(rng.choice([1, 2, 3, 5, 7, 8, 10, 16, 20])) if fila['tos'] else None
    fiebre = fila['temperatura'] is not None and fila['temperatura'] > 38
    fila['dias_fiebre'] = int(rng.choice([1, 2, 3, 5, 8, 9])) if fiebre else None
    return fila


def generar_dataset(filas=6000, semilla=2026):
    """Dataset SINTÉTICO etiquetado con las reglas clínicas vigentes (columna `nivel`)."""
    rng = np.random.default_rng(semilla)
    registros = []
    for _ in range(filas):
        fila = _fila_sintetica(rng)
        resultado = evaluar_v1(DatosEvaluacion(**fila))
        fila['nivel'] = resultado.nivel
        fila['reglas'] = ' '.join(s['regla_id'] for s in resultado.senales)
        registros.append(fila)
    return pd.DataFrame(registros, columns=[*VARIABLES, 'nivel', 'reglas'])


def matriz_variables(df):
    """Convierte las variables a números: booleanos 0/1 y datos faltantes como NaN (el bosque los admite)."""
    datos = df[list(VARIABLES)].copy()
    for columna in VARIABLES:
        datos[columna] = pd.to_numeric(datos[columna].astype('object').replace({True: 1, False: 0}), errors='coerce')
    return datos.astype(float)


def sha256_archivo(ruta):
    h = hashlib.sha256()
    with open(ruta, 'rb') as archivo:
        for bloque in iter(lambda: archivo.read(65536), b''):
            h.update(bloque)
    return h.hexdigest()


def entrenar(df, semilla=2026, arboles=200):
    """Entrena el bosque aleatorio y calcula métricas sobre una partición de prueba estratificada."""
    x, y = matriz_variables(df), df['nivel']
    x_ent, x_prueba, y_ent, y_prueba = train_test_split(x, y, test_size=0.25, random_state=semilla, stratify=y)
    hiperparametros = {'n_estimators': arboles, 'max_depth': 12, 'class_weight': 'balanced',
                       'random_state': semilla, 'n_jobs': -1}
    modelo = RandomForestClassifier(**hiperparametros).fit(x_ent, y_ent)

    pred = modelo.predict(x_prueba)
    matriz = confusion_matrix(y_prueba, pred, labels=list(CLASES))
    recall = recall_score(y_prueba, pred, labels=list(CLASES), average=None, zero_division=0)
    metricas = {
        'exactitud': round(float(accuracy_score(y_prueba, pred)), 4),
        'f1_macro': round(float(f1_score(y_prueba, pred, average='macro')), 4),
        'sensibilidad_por_clase': {c: round(float(r), 4) for c, r in zip(CLASES, recall)},
        'matriz_confusion': {'filas_reales_columnas_predichas': list(CLASES), 'valores': matriz.tolist()},
        'rojos_predichos_como_verde': int(matriz[2][0]),
    }
    metadatos = {
        'version': VERSION_MODELO,
        'fecha_entrenamiento': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'algoritmo': 'RandomForestClassifier (scikit-learn)',
        'hiperparametros': {k: v for k, v in hiperparametros.items() if k != 'n_jobs'},
        'variables': list(VARIABLES),
        'clases': list(CLASES),
        'dataset': {
            'tipo': 'SINTÉTICO',
            'filas': int(len(df)), 'entrenamiento': int(len(x_ent)), 'prueba': int(len(x_prueba)),
            'distribucion_clases': {c: int((y == c).sum()) for c in CLASES},
            'etiquetado_por': f'reglas clínicas {VERSION_REGLAS}',
            'semilla': semilla,
        },
        'metricas_prueba': metricas,
        'limitaciones': list(LIMITACIONES),
        'uso_permitido': 'Apoyo complementario para profesionales y desarrollo técnico. No modifica la '
                         'clasificación clínica por reglas y no se muestra a cuidadores.',
        'entorno': {'python': platform.python_version(), 'scikit_learn': sklearn.__version__},
    }
    return modelo, metadatos


def guardar(modelo, metadatos, ruta_modelo, ruta_dataset=None):
    """Guarda el modelo y, junto a él, sus metadatos con el hash SHA-256 para verificar su integridad al cargarlo."""
    os.makedirs(os.path.dirname(ruta_modelo), exist_ok=True)
    joblib.dump(modelo, ruta_modelo, compress=3)
    metadatos = dict(metadatos, sha256_modelo=sha256_archivo(ruta_modelo))
    if ruta_dataset and os.path.exists(ruta_dataset):
        metadatos['dataset'] = dict(metadatos['dataset'], archivo=os.path.relpath(ruta_dataset).replace(os.sep, '/'),
                                    sha256=sha256_archivo(ruta_dataset))
    with open(ruta_metadatos(ruta_modelo), 'w', encoding='utf-8') as archivo:
        json.dump(metadatos, archivo, ensure_ascii=False, indent=2)
    return metadatos


def ruta_metadatos(ruta_modelo):
    return os.path.splitext(ruta_modelo)[0] + '.json'


def ficha_markdown(m):
    """Ficha del modelo (model card) en Markdown, generada desde los metadatos."""
    met = m['metricas_prueba']
    filas_matriz = '\n'.join(
        f'| {real} | ' + ' | '.join(str(v) for v in valores) + ' |'
        for real, valores in zip(m['clases'], met['matriz_confusion']['valores']))
    return '\n'.join([
        f'# Ficha del modelo ML complementario — {m["version"]}',
        '',
        '> Generado automáticamente con `flask ml entrenar`; no editar a mano.',
        '',
        '> ⚠️ **Modelo experimental entrenado con datos SINTÉTICOS. No tiene validación clínica y no debe usarse '
        'para decisiones de salud.** La clasificación que cuenta en RespiraKids es la de las reglas clínicas.',
        '',
        '## Resumen',
        '',
        f'- **Algoritmo:** {m["algoritmo"]} — hiperparámetros: `{json.dumps(m["hiperparametros"])}`',
        f'- **Fecha de entrenamiento (UTC):** {m["fecha_entrenamiento"]}',
        f'- **Entorno:** Python {m["entorno"]["python"]}, scikit-learn {m["entorno"]["scikit_learn"]}',
        f'- **Uso permitido:** {m["uso_permitido"]}',
        f'- **Integridad (SHA-256 del modelo):** `{m.get("sha256_modelo", "—")}`',
        '',
        '## Datos',
        '',
        f'- **Tipo:** {m["dataset"]["tipo"]} — {m["dataset"]["filas"]} filas '
        f'({m["dataset"]["entrenamiento"]} entrenamiento / {m["dataset"]["prueba"]} prueba), semilla '
        f'{m["dataset"]["semilla"]}.',
        f'- **Etiquetas:** asignadas por {m["dataset"]["etiquetado_por"]}.',
        f'- **Distribución de clases:** {m["dataset"]["distribucion_clases"]}',
        f'- **Archivo:** `{m["dataset"].get("archivo", "—")}` (SHA-256 `{m["dataset"].get("sha256", "—")}`)',
        '',
        '## Variables',
        '',
        'Las mismas que usa el motor clínico: ' + ', '.join(f'`{v}`' for v in m['variables']) + '.',
        '',
        '## Métricas sobre la partición de prueba',
        '',
        f'- **Exactitud:** {met["exactitud"]} — **F1 macro:** {met["f1_macro"]}',
        f'- **Sensibilidad por clase:** {met["sensibilidad_por_clase"]}',
        f'- **Casos rojos predichos como verde:** {met["rojos_predichos_como_verde"]}',
        '',
        '| Real \\ Predicho | ' + ' | '.join(m['clases']) + ' |',
        '|---|' + '---|' * len(m['clases']),
        filas_matriz,
        '',
        'Estas métricas miden qué tan bien el modelo **imita las reglas** en datos sintéticos, no su capacidad '
        'de predecir riesgo en niños reales.',
        '',
        '## Limitaciones',
        '',
        *[f'- {texto}' for texto in m['limitaciones']],
        '',
    ])
