"""Change assignment name data type

Revision ID: f3345539f08d
Revises: 6f2a6c00affb
Create Date: 2020-11-12 08:28:58.059493

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f3345539f08d"
down_revision = "6f2a6c00affb"
branch_labels = None
depends_on = None


def upgrade():

    with op.batch_alter_table("assignment") as batch_op:
        batch_op.alter_column(
            "assignment_code", "assignment_code", existing_type=sa.VARCHAR(length=50), type_=sa.Text()
        )


def downgrade():

    with op.batch_alter_table("assignment") as batch_op:
        batch_op.alter_column(
            "assignment_code", "assignment_code", existing_type=sa.Text(), type_=sa.VARCHAR(length=50)
        )
