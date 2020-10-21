"""Add feedback to ation enum type

Revision ID: 6f2a6c00affb
Revises: 2805bf7747e5
Create Date: 2020-10-21 13:55:01.264068

"""
from alembic import op
import sqlalchemy as sa

from datetime import datetime
from enum import Enum

# revision identifiers, used by Alembic.
revision = '6f2a6c00affb'
down_revision = '2805bf7747e5'
branch_labels = None
depends_on = None


class NewAssignmentActions(Enum):
    released = "released"
    fetched = "fetched"
    submitted = "submitted"
    removed = "removed"
    collected = "collected"
    feedback_released = "feedback_released"
    feedback_fetched = "feedback_fetched"


class OldAssignmentActions(Enum):
    released = "released"
    fetched = "fetched"
    submitted = "submitted"
    removed = "removed"
    collected = "collected"


def upgrade():

    connection = op.get_bind()
    
    if connection.dialect.name == "postgresql":

        op.execute("ALTER TYPE assignmentactions ADD VALUE IF NOT EXISTS feedback_released")
        op.execute("ALTER TYPE assignmentactions ADD VALUE IF NOT EXISTS feedback_fetched") 

    else:

        with op.batch_alter_table("action") as batch_op:

            batch_op.alter_column(
                "action",
                "action",
                existing_type=sa.Enum(OldAssignmentActions, name="assignmentactions"),
                type_=sa.Enum(NewAssignmentActions, name="assignmentactions"),
            )


def downgrade():

    if connection.dialect.name == "postgresql":
        pass
    else:
        with op.batch_alter_table("action") as batch_op:
            batch_op.alter_column(
                "action",
                "action",
                existing_type=sa.Enum(NewAssignmentActions, name="assignmentactions"),
                type_=sa.Enum(OldAssignmentActions, name="assignmentactions"),
            )