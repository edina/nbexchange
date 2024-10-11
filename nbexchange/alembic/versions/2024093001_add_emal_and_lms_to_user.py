"""Add email address and lms_user_id to usertable

Revision ID: 2024093001
Revises: bfe19408f64f
Create Date: 2019-04-02 15:40

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2024093001"
down_revision = "2540572282f2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.add_column(sa.Column("email", sa.Text, nullable=True))
        batch_op.add_column(sa.Column("lms_user_id", sa.Text, nullable=True))


def downgrade():
    with op.batch_alter_table("user") as batch_op:
        batch_op.drop_column("email")
        batch_op.drop_column("lms_user_id")
