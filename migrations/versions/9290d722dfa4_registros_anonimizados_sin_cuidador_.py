"""registros anonimizados sin cuidador asociado

Revision ID: 9290d722dfa4
Revises: ae1e8f667adf
Create Date: 2026-10-01 21:43:15.760573

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9290d722dfa4'
down_revision = 'ae1e8f667adf'
branch_labels = None
depends_on = None


def upgrade():
    # Solo permite valores vacíos (registros anonimizados por supresión); no modifica datos existentes.
    with op.batch_alter_table('ninos', schema=None) as batch_op:
        batch_op.alter_column('cuidador_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    with op.batch_alter_table('seguimientos_evolucion', schema=None) as batch_op:
        batch_op.alter_column('cuidador_id',
               existing_type=sa.INTEGER(),
               nullable=True)



def downgrade():
    # Fallará si ya existen registros anonimizados (sin cuidador): es intencional, no se pierden datos.
    with op.batch_alter_table('seguimientos_evolucion', schema=None) as batch_op:
        batch_op.alter_column('cuidador_id',
               existing_type=sa.INTEGER(),
               nullable=False)

    with op.batch_alter_table('ninos', schema=None) as batch_op:
        batch_op.alter_column('cuidador_id',
               existing_type=sa.INTEGER(),
               nullable=False)

