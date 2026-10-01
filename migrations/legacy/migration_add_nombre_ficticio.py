"""
Script para agregar la columna nombre_ficticio a la tabla ninos.
Ejecutar con: python migration_add_nombre_ficticio.py
"""

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Verificar si la columna ya existe
    result = db.session.execute(text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'ninos' AND column_name = 'nombre_ficticio'
    """))
    
    if result.fetchone():
        print("La columna 'nombre_ficticio' ya existe en la tabla 'ninos'.")
    else:
        # Agregar la columna
        db.session.execute(text("""
            ALTER TABLE ninos 
            ADD COLUMN nombre_ficticio VARCHAR(100) NOT NULL DEFAULT 'Sin nombre'
        """))
        db.session.commit()
        print("✅ Columna 'nombre_ficticio' agregada exitosamente a la tabla 'ninos'.")
