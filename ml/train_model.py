"""Entrena un modelo de clasificación de riesgo con el dataset sintético."""
import pandas as pd
import joblib
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

df = pd.read_csv('ml/dataset.csv')

FEATURES = [
    'edad_meses', 'temperatura', 'severidad', 'dias_inicio',
    'tos', 'dificultad_respiratoria', 'respiracion_rapida',
    'congestion_nasal', 'secrecion_nasal', 'dolor_garganta',
    'decaimiento', 'perdida_apetito', 'vomito', 'diarrea',
    'estornudos', 'irritabilidad', 'condicion_asma', 'condicion_alergias',
    'num_patologias_base', 'num_episodios_previos'
]

X = df[FEATURES]
y = df['nivel_riesgo']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

modelo = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42, class_weight='balanced')
modelo.fit(X_train, y_train)

y_pred = modelo.predict(X_test)
print(classification_report(y_test, y_pred, target_names=['verde', 'amarillo', 'rojo']))

os.makedirs('app/ml_models', exist_ok=True)
joblib.dump({'modelo': modelo, 'features': FEATURES}, 'app/ml_models/riesgo_model.pkl')
print("Modelo guardado en app/ml_models/riesgo_model.pkl")