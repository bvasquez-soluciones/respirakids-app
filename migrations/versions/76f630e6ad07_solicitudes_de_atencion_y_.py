"""solicitudes de atencion y disponibilidad de profesionales

Revision ID: 76f630e6ad07
Revises: 9290d722dfa4
Create Date: 2026-10-01 22:56:11.967223

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '76f630e6ad07'
down_revision = '9290d722dfa4'
branch_labels = None
depends_on = None


def upgrade():
    # Aditiva: crea la tabla de solicitudes y la columna de disponibilidad (todos disponibles por defecto).
    op.create_table('solicitudes_atencion',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nino_id', sa.Integer(), nullable=False),
    sa.Column('cuidador_id', sa.Integer(), nullable=True),
    sa.Column('profesional_id', sa.Integer(), nullable=True),
    sa.Column('evaluacion_id', sa.Integer(), nullable=True),
    sa.Column('motivo', sa.Text(), nullable=False),
    sa.Column('estado', sa.String(length=15), server_default='pendiente', nullable=False),
    sa.Column('acceso', sa.String(length=10), nullable=True),
    sa.Column('fecha_creacion', sa.DateTime(), nullable=False),
    sa.Column('fecha_asignacion', sa.DateTime(), nullable=True),
    sa.Column('fecha_cierre', sa.DateTime(), nullable=True),
    sa.CheckConstraint("acceso IS NULL OR acceso IN ('otorgado', 'denegado')", name='ck_solicitudes_atencion_acceso'),
    sa.CheckConstraint("estado IN ('pendiente', 'asignada', 'cerrada', 'cancelada')", name='ck_solicitudes_atencion_estado'),
    sa.ForeignKeyConstraint(['cuidador_id'], ['cuidadores.id'], ),
    sa.ForeignKeyConstraint(['evaluacion_id'], ['evaluaciones.id'], ),
    sa.ForeignKeyConstraint(['nino_id'], ['ninos.id'], ),
    sa.ForeignKeyConstraint(['profesional_id'], ['profesionales.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('solicitudes_atencion', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_solicitudes_atencion_cuidador_id'), ['cuidador_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_solicitudes_atencion_estado'), ['estado'], unique=False)
        batch_op.create_index(batch_op.f('ix_solicitudes_atencion_nino_id'), ['nino_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_solicitudes_atencion_profesional_id'), ['profesional_id'], unique=False)

    with op.batch_alter_table('profesionales', schema=None) as batch_op:
        batch_op.add_column(sa.Column('disponible', sa.Boolean(), server_default=sa.true(), nullable=False))



def downgrade():
    with op.batch_alter_table('profesionales', schema=None) as batch_op:
        batch_op.drop_column('disponible')

    with op.batch_alter_table('solicitudes_atencion', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_solicitudes_atencion_profesional_id'))
        batch_op.drop_index(batch_op.f('ix_solicitudes_atencion_nino_id'))
        batch_op.drop_index(batch_op.f('ix_solicitudes_atencion_estado'))
        batch_op.drop_index(batch_op.f('ix_solicitudes_atencion_cuidador_id'))

    op.drop_table('solicitudes_atencion')
