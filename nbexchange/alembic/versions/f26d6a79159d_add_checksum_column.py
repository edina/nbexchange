"""Add checksum column

Revision ID: f26d6a79159d
Revises: 20190202
Create Date: 2020-03-17 11:28:26.163498

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f26d6a79159d"
down_revision = "20190202"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("action") as batch_op:
        batch_op.add_column(
            sa.Column("checksum", sa.Unicode(length=200), nullable=True)
        )
        batch_op.alter_column(
            "action", existing_type=sa.VARCHAR(length=9), nullable=False
        )


def downgrade():
    with op.batch_alter_table("action") as batch_op:
        batch_op.alter_column(
            "action", existing_type=sa.VARCHAR(length=9), nullable=True
        )
        batch_op.drop_column("checksum")
