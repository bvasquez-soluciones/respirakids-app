# Ficha del modelo ML complementario — ml-v1-sintetico

> Generado automáticamente con `flask ml entrenar`; no editar a mano.

> ⚠️ **Modelo experimental entrenado con datos SINTÉTICOS. No tiene validación clínica y no debe usarse para decisiones de salud.** La clasificación que cuenta en RespiraKids es la de las reglas clínicas.

## Resumen

- **Algoritmo:** RandomForestClassifier (scikit-learn) — hiperparámetros: `{"n_estimators": 200, "max_depth": 12, "class_weight": "balanced", "random_state": 2026}`
- **Fecha de entrenamiento (UTC):** 2026-10-01T20:58:32+00:00
- **Entorno:** Python 3.14.4, scikit-learn 1.9.0
- **Uso permitido:** Apoyo complementario para profesionales y desarrollo técnico. No modifica la clasificación clínica por reglas y no se muestra a cuidadores.
- **Integridad (SHA-256 del modelo):** `8a7ebcce4d0d1b73edc6dd5c655de30bbbe82b570ef074d420e0d1c3afa52d12`

## Datos

- **Tipo:** SINTÉTICO — 6000 filas (4500 entrenamiento / 1500 prueba), semilla 2026.
- **Etiquetas:** asignadas por reglas clínicas v1-aiepi.
- **Distribución de clases:** {'verde': 2060, 'amarillo': 2333, 'rojo': 1607}
- **Archivo:** `ml/datos/dataset_sintetico_v1.csv` (SHA-256 `33670364a5e508fac0b92f62aaa815ff1c30fe03e3438d2c38d5e1e9ece1748e`)

## Variables

Las mismas que usa el motor clínico: `edad_meses`, `temperatura`, `frecuencia_respiratoria`, `spo2`, `altitud_msnm`, `dias_tos`, `dias_fiebre`, `tos`, `dificultad_respiratoria`, `respiracion_rapida`, `congestion_nasal`, `secrecion_nasal`, `dolor_garganta`, `estornudos`, `sibilancias`, `estridor`, `tiraje_subcostal`, `cianosis`, `incapacidad_beber_liquidos`, `aleteo_nasal`, `quejido`, `apnea`, `convulsion`, `alteracion_conciencia`, `rigidez_cuello`, `abombamiento_fontanela`, `petequias`, `edema_retroauricular`, `tos_paroxistica`, `vomito_tras_tos`, `contacto_tuberculosis`, `perdida_peso`, `disminucion_actividad`, `factor_riesgo_bar`.

## Métricas sobre la partición de prueba

- **Exactitud:** 0.8933 — **F1 macro:** 0.8952
- **Sensibilidad por clase:** {'verde': 0.9631, 'amarillo': 0.8611, 'rojo': 0.8507}
- **Casos rojos predichos como verde:** 22

| Real \ Predicho | verde | amarillo | rojo |
|---|---|---|---|
| verde | 496 | 17 | 2 |
| amarillo | 75 | 502 | 6 |
| rojo | 22 | 38 | 342 |

Estas métricas miden qué tan bien el modelo **imita las reglas** en datos sintéticos, no su capacidad de predecir riesgo en niños reales.

## Limitaciones

- Entrenado con datos SINTÉTICOS (generados por programa), no con casos reales.
- Las etiquetas las asignan las reglas clínicas v1-aiepi: el modelo aprende a imitarlas y hereda sus limitaciones, incluida su validación clínica pendiente.
- Las proporciones de cada síntoma en el dataset son supuestos del generador, no epidemiología real.
- Una exactitud alta solo indica que imita bien las reglas; no indica capacidad de predecir riesgo real.
- No es un dispositivo médico ni una herramienta validada: su resultado no debe usarse para decisiones clínicas.
- Para un uso real debe reentrenarse con datos reales anonimizados, etiquetados por profesionales y evaluarse de forma independiente.
