"""adjuntos de mensajes

Revision ID: 64455eb5cf9b
Revises: 76f630e6ad07
Create Date: 2026-10-02 09:03:35.791805

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '64455eb5cf9b'
down_revision = '76f630e6ad07'
branch_labels = None
depends_on = None


def upgrade():
    # Aditiva: solo crea la tabla de adjuntos (los archivos van a ADJUNTOS_FOLDER, fuera de la base).
    op.create_table('adjuntos_mensaje',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('mensaje_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.String(length=10), nullable=False),
    sa.Column('mime', sa.String(length=60), nullable=False),
    sa.Column('archivo', sa.String(length=80), nullable=False),
    sa.Column('nombre_original', sa.String(length=150), nullable=False),
    sa.Column('tamano', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.DateTime(), nullable=False),
    sa.CheckConstraint("tipo IN ('imagen', 'documento', 'audio')", name='ck_adjuntos_mensaje_tipo'),
    sa.ForeignKeyConstraint(['mensaje_id'], ['mensajes.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('archivo')
    )
    with op.batch_alter_table('adjuntos_mensaje', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_adjuntos_mensaje_mensaje_id'), ['mensaje_id'], unique=False)



def downgrade():
    with op.batch_alter_table('adjuntos_mensaje', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_adjuntos_mensaje_mensaje_id'))

    op.drop_table('adjuntos_mensaje')
