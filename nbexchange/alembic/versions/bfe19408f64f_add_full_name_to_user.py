"""add full_name to user

Revision ID: bfe19408f64f
Revises: f3345539f08d
Create Date: 2021-04-13 11:42:48.373791

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "bfe19408f64f"
down_revision = "f3345539f08d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(sa.Column("full_name", sa.Text, nullable=True))


def downgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("full_name")
