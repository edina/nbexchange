"""Add external id column

Revision ID: 7aa7d804f8ef
Revises: f3345539f08d
Create Date: 2021-03-12 15:54:10.126297

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7aa7d804f8ef'
down_revision = 'f3345539f08d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('ext_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_user_ext_id'), 'user', ['ext_id'], unique=True)


def downgrade():
    op.drop_index(op.f('ix_user_ext_id'), table_name='user')
    op.drop_column('user', 'ext_id')
