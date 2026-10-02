"""seguimiento de evolucion reportado por el cuidador

Revision ID: ae1e8f667adf
Revises: c2344ae9d2e3
Create Date: 2026-10-01 18:39:00.628155

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ae1e8f667adf'
down_revision = 'c2344ae9d2e3'
branch_labels = None
depends_on = None


def upgrade():
    # Solo crea una tabla nueva: no modifica tablas ni datos existentes.
    op.create_table('seguimientos_evolucion',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nino_id', sa.Integer(), nullable=False),
    sa.Column('cuidador_id', sa.Integer(), nullable=False),
    sa.Column('evaluacion_id', sa.Integer(), nullable=True),
    sa.Column('estado', sa.String(length=10), nullable=False),
    sa.Column('fecha', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['cuidador_id'], ['cuidadores.id'], ),
    sa.ForeignKeyConstraint(['evaluacion_id'], ['evaluaciones.id'], ),
    sa.ForeignKeyConstraint(['nino_id'], ['ninos.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.CheckConstraint("estado IN ('mejoro', 'igual', 'empeoro')", name='ck_seguimientos_evolucion_estado'),
    )
    with op.batch_alter_table('seguimientos_evolucion', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_seguimientos_evolucion_cuidador_id'), ['cuidador_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_seguimientos_evolucion_evaluacion_id'), ['evaluacion_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_seguimientos_evolucion_fecha'), ['fecha'], unique=False)
        batch_op.create_index(batch_op.f('ix_seguimientos_evolucion_nino_id'), ['nino_id'], unique=False)



def downgrade():
    with op.batch_alter_table('seguimientos_evolucion', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_seguimientos_evolucion_nino_id'))
        batch_op.drop_index(batch_op.f('ix_seguimientos_evolucion_fecha'))
        batch_op.drop_index(batch_op.f('ix_seguimientos_evolucion_evaluacion_id'))
        batch_op.drop_index(batch_op.f('ix_seguimientos_evolucion_cuidador_id'))

    op.drop_table('seguimientos_evolucion')
