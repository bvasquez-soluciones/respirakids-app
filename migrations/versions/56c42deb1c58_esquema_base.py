"""Esquema base de RespiraKids (línea base de producción).

Representa el esquema completo que existe en la base de datos en esta revisión.
Las migraciones anteriores (incompletas respecto al esquema real) se archivaron
en migrations/legacy/ y ya no forman parte de la cadena de Alembic.

- Base de datos existente: ya se encuentra en esta revisión; no se ejecuta nada.
- Base de datos nueva: `flask db upgrade` crea todas las tablas.

Revision ID: 56c42deb1c58
Revises:
Create Date: 2026-10-01
"""
from alembic import op
import sqlalchemy as sa


revision = '56c42deb1c58'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('cuidadores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('apellido', sa.String(length=100), nullable=True),
    sa.Column('correo', sa.String(length=120), nullable=False),
    sa.Column('telefono', sa.String(length=30), nullable=True),
    sa.Column('tipo_documento', sa.String(length=20), nullable=True),
    sa.Column('numero_documento', sa.String(length=30), nullable=True),
    sa.Column('fecha_nacimiento', sa.Date(), nullable=True),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('rol', sa.String(length=20), server_default='cuidador', nullable=False),
    sa.Column('fecha_registro', sa.DateTime(), nullable=True),
    sa.Column('intentos_fallidos', sa.Integer(), nullable=True),
    sa.Column('bloqueado_hasta', sa.DateTime(), nullable=True),
    sa.Column('correo_verificado', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('token_verificacion', sa.String(length=100), nullable=True),
    sa.Column('token_verificacion_expira', sa.DateTime(), nullable=True),
    sa.Column('token_recuperacion', sa.String(length=100), nullable=True),
    sa.Column('token_recuperacion_expira', sa.DateTime(), nullable=True),
    sa.Column('notificaciones_vistas_hasta', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('correo')
    )
    op.create_table('fuentes_conocimiento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=150), nullable=False),
    sa.Column('tipo', sa.String(length=50), nullable=True),
    sa.Column('url', sa.String(length=500), nullable=True),
    sa.Column('fecha_publicacion', sa.Date(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('logs_actividad',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=True),
    sa.Column('usuario_tipo', sa.String(length=20), nullable=True),
    sa.Column('accion', sa.String(length=50), nullable=False),
    sa.Column('recurso', sa.String(length=50), nullable=True),
    sa.Column('recurso_id', sa.Integer(), nullable=True),
    sa.Column('detalles', sa.Text(), nullable=True),
    sa.Column('resultado', sa.String(length=20), nullable=True),
    sa.Column('ip', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.String(length=500), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('logs_seguridad',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=True),
    sa.Column('usuario_tipo', sa.String(length=20), nullable=True),
    sa.Column('evento', sa.String(length=50), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=True),
    sa.Column('ip', sa.String(length=45), nullable=True),
    sa.Column('user_agent', sa.String(length=500), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('notificaciones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=False),
    sa.Column('usuario_tipo', sa.String(length=20), nullable=False),
    sa.Column('tipo', sa.String(length=50), nullable=False),
    sa.Column('titulo', sa.String(length=200), nullable=False),
    sa.Column('contenido', sa.Text(), nullable=False),
    sa.Column('recurso', sa.String(length=50), nullable=True),
    sa.Column('recurso_id', sa.Integer(), nullable=True),
    sa.Column('leida', sa.Boolean(), nullable=False),
    sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
    sa.Column('fecha_lectura', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('profesionales',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('apellido', sa.String(length=100), nullable=True),
    sa.Column('correo', sa.String(length=120), nullable=False),
    sa.Column('telefono', sa.String(length=30), nullable=True),
    sa.Column('tipo_documento', sa.String(length=20), nullable=True),
    sa.Column('numero_documento', sa.String(length=30), nullable=True),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('rol', sa.String(length=20), nullable=False),
    sa.Column('fecha_registro', sa.DateTime(), nullable=True),
    sa.Column('foto', sa.String(length=255), nullable=True),
    sa.Column('profesion', sa.String(length=100), nullable=True),
    sa.Column('especialidad', sa.String(length=100), nullable=True),
    sa.Column('numero_licencia', sa.String(length=50), nullable=True),
    sa.Column('tarjeta_profesional', sa.String(length=50), nullable=True),
    sa.Column('registro_rethus', sa.String(length=50), nullable=True),
    sa.Column('estado_aprobacion', sa.String(length=20), server_default='aprobado', nullable=False),
    sa.Column('intentos_fallidos', sa.Integer(), nullable=True),
    sa.Column('bloqueado_hasta', sa.DateTime(), nullable=True),
    sa.Column('token_recuperacion', sa.String(length=100), nullable=True),
    sa.Column('token_recuperacion_expira', sa.DateTime(), nullable=True),
    sa.Column('notificaciones_vistas_hasta', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('correo')
    )
    op.create_table('versiones_registro',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tabla', sa.String(length=50), nullable=False),
    sa.Column('registro_id', sa.Integer(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('accion', sa.String(length=20), nullable=False),
    sa.Column('datos', sa.Text(), nullable=False),
    sa.Column('usuario_id', sa.Integer(), nullable=True),
    sa.Column('usuario_tipo', sa.String(length=20), nullable=True),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('conocimientos_sanitarios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('fuente_id', sa.Integer(), nullable=False),
    sa.Column('categoria', sa.String(length=100), nullable=False),
    sa.Column('nivel', sa.String(length=50), nullable=False),
    sa.Column('titulo', sa.String(length=200), nullable=False),
    sa.Column('contenido', sa.Text(), nullable=False),
    sa.Column('tipo_contenido', sa.String(length=50), nullable=True),
    sa.Column('restricciones', sa.Text(), nullable=True),
    sa.Column('edad_min_meses', sa.Integer(), nullable=True),
    sa.Column('edad_max_meses', sa.Integer(), nullable=True),
    sa.Column('fecha_actualizacion', sa.Date(), nullable=False),
    sa.Column('activo', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['fuente_id'], ['fuentes_conocimiento.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('ninos',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cuidador_id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=100), nullable=False),
    sa.Column('apellido', sa.String(length=100), nullable=True),
    sa.Column('tipo_documento', sa.String(length=20), nullable=True),
    sa.Column('numero_documento', sa.String(length=30), nullable=True),
    sa.Column('fecha_nacimiento', sa.Date(), nullable=False),
    sa.Column('sexo', sa.String(length=1), nullable=False),
    sa.Column('peso_kg', sa.Float(), nullable=True),
    sa.Column('talla_cm', sa.Float(), nullable=True),
    sa.Column('estado', sa.String(length=20), nullable=True),
    sa.Column('fecha_registro', sa.DateTime(), nullable=True),
    sa.Column('consentimiento_otorgado', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('consentimiento_fecha', sa.DateTime(), nullable=True),
    sa.Column('consentimiento_ip', sa.String(length=45), nullable=True),
    sa.Column('consentimiento_investigacion_otorgado', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('consentimiento_investigacion_fecha', sa.DateTime(), nullable=True),
    sa.Column('consentimiento_investigacion_ip', sa.String(length=45), nullable=True),
    sa.Column('nombre_ficticio', sa.String(length=100), server_default='Sin nombre', nullable=False),
    sa.ForeignKeyConstraint(['cuidador_id'], ['cuidadores.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('autorizaciones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nino_id', sa.Integer(), nullable=False),
    sa.Column('profesional_id', sa.Integer(), nullable=False),
    sa.Column('fecha_autorizacion', sa.DateTime(), nullable=True),
    sa.Column('fecha_expiracion', sa.DateTime(), nullable=True),
    sa.Column('activa', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['nino_id'], ['ninos.id'], ),
    sa.ForeignKeyConstraint(['profesional_id'], ['profesionales.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('consultas_ia',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nino_id', sa.Integer(), nullable=False),
    sa.Column('cuidador_id', sa.Integer(), nullable=False),
    sa.Column('categoria_sintoma', sa.String(length=50), nullable=True),
    sa.Column('contexto_json', sa.Text(), nullable=True),
    sa.Column('resultado', sa.String(length=30), nullable=True),
    sa.Column('fuentes_citadas', sa.Text(), nullable=True),
    sa.Column('fecha', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['cuidador_id'], ['cuidadores.id'], ),
    sa.ForeignKeyConstraint(['nino_id'], ['ninos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('mensajes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nino_id', sa.Integer(), nullable=False),
    sa.Column('profesional_conversacion_id', sa.Integer(), nullable=True),
    sa.Column('autor_tipo', sa.String(length=20), nullable=False),
    sa.Column('autor_cuidador_id', sa.Integer(), nullable=True),
    sa.Column('autor_profesional_id', sa.Integer(), nullable=True),
    sa.Column('contenido', sa.Text(), nullable=False),
    sa.Column('fecha', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['autor_cuidador_id'], ['cuidadores.id'], ),
    sa.ForeignKeyConstraint(['autor_profesional_id'], ['profesionales.id'], ),
    sa.ForeignKeyConstraint(['nino_id'], ['ninos.id'], ),
    sa.ForeignKeyConstraint(['profesional_conversacion_id'], ['profesionales.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('patologias_base',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nino_id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=150), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=True),
    sa.Column('fecha_diagnostico', sa.Date(), nullable=True),
    sa.Column('activa', sa.Boolean(), nullable=True),
    sa.Column('fecha_registro', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['nino_id'], ['ninos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('recetas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nino_id', sa.Integer(), nullable=False),
    sa.Column('profesional_id', sa.Integer(), nullable=False),
    sa.Column('motivo', sa.String(length=255), nullable=True),
    sa.Column('indicaciones_generales', sa.Text(), nullable=True),
    sa.Column('fecha', sa.DateTime(), nullable=True),
    sa.Column('activa', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['nino_id'], ['ninos.id'], ),
    sa.ForeignKeyConstraint(['profesional_id'], ['profesionales.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('registros_sintomas',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nino_id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.DateTime(), nullable=True),
    sa.Column('tipo', sa.String(length=20), server_default='sintomas', nullable=False),
    sa.Column('estado_evolucion', sa.String(length=20), nullable=True),
    sa.Column('temperatura', sa.Float(), nullable=True),
    sa.Column('tos', sa.Boolean(), nullable=True),
    sa.Column('dificultad_respiratoria', sa.Boolean(), nullable=True),
    sa.Column('respiracion_rapida', sa.Boolean(), nullable=True),
    sa.Column('congestion_nasal', sa.Boolean(), nullable=True),
    sa.Column('secrecion_nasal', sa.Boolean(), nullable=True),
    sa.Column('dolor_garganta', sa.Boolean(), nullable=True),
    sa.Column('decaimiento', sa.Boolean(), nullable=True),
    sa.Column('perdida_apetito', sa.Boolean(), nullable=True),
    sa.Column('vomito', sa.Boolean(), nullable=True),
    sa.Column('diarrea', sa.Boolean(), nullable=True),
    sa.Column('estornudos', sa.Boolean(), nullable=True),
    sa.Column('irritabilidad', sa.Boolean(), nullable=True),
    sa.Column('otros_sintomas', sa.Text(), nullable=True),
    sa.Column('observaciones', sa.Text(), nullable=True),
    sa.Column('severidad', sa.Integer(), nullable=True),
    sa.Column('inicio_sintomas', sa.String(length=20), nullable=True),
    sa.Column('dias_sintomas', sa.Integer(), nullable=True),
    sa.Column('condicion_asma', sa.Boolean(), nullable=True),
    sa.Column('condicion_alergias', sa.Boolean(), nullable=True),
    sa.Column('frecuencia_respiratoria', sa.Integer(), nullable=True),
    sa.Column('frecuencia_cardiaca', sa.Integer(), nullable=True),
    sa.Column('spo2', sa.Float(), nullable=True),
    sa.Column('tiraje_subcostal', sa.Boolean(), server_default=sa.false(), nullable=True),
    sa.Column('cianosis', sa.Boolean(), server_default=sa.false(), nullable=True),
    sa.Column('incapacidad_beber_liquidos', sa.Boolean(), server_default=sa.false(), nullable=True),
    sa.Column('aleteo_nasal', sa.Boolean(), nullable=True),
    sa.Column('quejido', sa.Boolean(), nullable=True),
    sa.Column('estridor', sa.Boolean(), nullable=True),
    sa.Column('uso_musculos_accesorios', sa.Boolean(), nullable=True),
    sa.Column('apnea', sa.Boolean(), nullable=True),
    sa.Column('convulsion', sa.Boolean(), nullable=True),
    sa.Column('palidez_extrema', sa.Boolean(), nullable=True),
    sa.Column('alteracion_conciencia', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['nino_id'], ['ninos.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('evaluaciones',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nino_id', sa.Integer(), nullable=False),
    sa.Column('registro_sintomas_id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.DateTime(), nullable=True),
    sa.Column('nivel_riesgo', sa.String(length=10), nullable=False),
    sa.Column('motivo', sa.Text(), nullable=True),
    sa.Column('recomendaciones', sa.Text(), nullable=True),
    sa.Column('ml_nivel_riesgo', sa.String(length=10), nullable=True),
    sa.Column('ml_confianza', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['nino_id'], ['ninos.id'], ),
    sa.ForeignKeyConstraint(['registro_sintomas_id'], ['registros_sintomas.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('medicamentos_recetados',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('receta_id', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(length=150), nullable=False),
    sa.Column('dosis', sa.String(length=100), nullable=False),
    sa.Column('frecuencia_horas', sa.Integer(), nullable=False),
    sa.Column('duracion_dias', sa.Integer(), nullable=True),
    sa.Column('instrucciones', sa.Text(), nullable=True),
    sa.Column('fecha_inicio', sa.DateTime(), nullable=True),
    sa.Column('activo', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['receta_id'], ['recetas.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('tomas_medicamento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('medicamento_id', sa.Integer(), nullable=False),
    sa.Column('hora_programada', sa.DateTime(), nullable=False),
    sa.Column('administrada', sa.Boolean(), nullable=True),
    sa.Column('hora_administrada', sa.DateTime(), nullable=True),
    sa.Column('administrado_por_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['administrado_por_id'], ['cuidadores.id'], ),
    sa.ForeignKeyConstraint(['medicamento_id'], ['medicamentos_recetados.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('tomas_medicamento')
    op.drop_table('medicamentos_recetados')
    op.drop_table('evaluaciones')
    op.drop_table('registros_sintomas')
    op.drop_table('recetas')
    op.drop_table('patologias_base')
    op.drop_table('mensajes')
    op.drop_table('consultas_ia')
    op.drop_table('autorizaciones')
    op.drop_table('ninos')
    op.drop_table('conocimientos_sanitarios')
    op.drop_table('versiones_registro')
    op.drop_table('profesionales')
    op.drop_table('notificaciones')
    op.drop_table('logs_seguridad')
    op.drop_table('logs_actividad')
    op.drop_table('fuentes_conocimiento')
    op.drop_table('cuidadores')
