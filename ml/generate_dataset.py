"""Genera un dataset sintético (ficticio) para entrenar el modelo de riesgo."""
import numpy as np
import pandas as pd

np.random.seed(42)
N = 3000

def generar_fila():
    edad_meses = np.random.randint(1, 144)
    temperatura = round(np.random.normal(37.3, 1.0), 1)
    severidad = np.random.randint(1, 11)
    dias_inicio = np.random.choice([0, 1, 2, 3], p=[0.4, 0.25, 0.2, 0.15])  # 0=hoy,1=ayer,2=2-3d,3=+3d
    tos = np.random.rand() < 0.5
    dificultad_respiratoria = np.random.rand() < 0.15
    respiracion_rapida = np.random.rand() < 0.15
    congestion_nasal = np.random.rand() < 0.4
    secrecion_nasal = np.random.rand() < 0.35
    dolor_garganta = np.random.rand() < 0.25
    decaimiento = np.random.rand() < 0.3
    perdida_apetito = np.random.rand() < 0.25
    vomito = np.random.rand() < 0.1
    diarrea = np.random.rand() < 0.1
    estornudos = np.random.rand() < 0.3
    irritabilidad = np.random.rand() < 0.25
    condicion_asma = np.random.rand() < 0.12
    condicion_alergias = np.random.rand() < 0.15
    num_patologias_base = int(condicion_asma) + int(condicion_alergias)
    num_episodios_previos = np.random.poisson(1.2)

    # --- Puntaje de riesgo "verdadero" con ruido, para que el modelo tenga que aprender patrones ---
    score = 0
    score += 3 if dificultad_respiratoria else 0
    score += 3 if respiracion_rapida else 0
    score += 2 if temperatura >= 39 else (1 if temperatura >= 38 else 0)
    score += 2 if severidad >= 8 else (1 if severidad >= 5 else 0)
    score += 1 if decaimiento and perdida_apetito else 0
    score += 1 if dias_inicio >= 3 else 0
    score += 1 if condicion_asma and (tos or dificultad_respiratoria) else 0
    score += 1 if edad_meses < 6 and (dificultad_respiratoria or temperatura >= 38.5) else 0
    score += np.random.normal(0, 0.7)  # ruido para simular incertidumbre real

    if score >= 4.5:
        nivel = 2  # rojo
    elif score >= 2:
        nivel = 1  # amarillo
    else:
        nivel = 0  # verde

    return dict(
        edad_meses=edad_meses, temperatura=temperatura, severidad=severidad, dias_inicio=dias_inicio,
        tos=int(tos), dificultad_respiratoria=int(dificultad_respiratoria), respiracion_rapida=int(respiracion_rapida),
        congestion_nasal=int(congestion_nasal), secrecion_nasal=int(secrecion_nasal), dolor_garganta=int(dolor_garganta),
        decaimiento=int(decaimiento), perdida_apetito=int(perdida_apetito), vomito=int(vomito), diarrea=int(diarrea),
        estornudos=int(estornudos), irritabilidad=int(irritabilidad),
        condicion_asma=int(condicion_asma), condicion_alergias=int(condicion_alergias),
        num_patologias_base=num_patologias_base, num_episodios_previos=num_episodios_previos,
        nivel_riesgo=nivel
    )

df = pd.DataFrame([generar_fila() for _ in range(N)])
df.to_csv('ml/dataset.csv', index=False)
print(f"Dataset generado: {len(df)} filas -> ml/dataset.csv")
print(df['nivel_riesgo'].value_counts())