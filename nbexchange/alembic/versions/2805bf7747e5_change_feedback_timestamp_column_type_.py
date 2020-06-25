"""Change feedback timestamp column type to DateTime
Revision ID: 2805bf7747e5
Revises: f26d6a79159d
Create Date: 2020-06-23 13:58:38.781382
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2805bf7747e5"
down_revision = "f26d6a79159d"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("feedback") as batch_op:
        batch_op.alter_column(
            "timestamp", existing_type=sa.VARCHAR(length=12), type_=sa.DateTime(timezone=True)
        )
    with op.batch_alter_table("action") as batch_op:
        batch_op.alter_column(
            "timestamp", existing_type=sa.DateTime, type_=sa.DateTime(timezone=True),
        )


def downgrade():
    with op.batch_alter_table("feedback") as batch_op:
        batch_op.alter_column(
            "timestamp", existing_type=sa.DateTime(timezone=True), type_=sa.VARCHAR(length=12),
        )
    with op.batch_alter_table("action") as batch_op:
        batch_op.alter_column(
            "timestamp", existing_type=sa.DateTime(timezone=True), type_=sa.DateTime,
        )
