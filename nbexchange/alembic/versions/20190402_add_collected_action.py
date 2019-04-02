"""Add item to Action Enum table 

Revision ID: 20190202
Revises: d500457efb3b
Create Date: 2019-04-02 15:40

"""
import sqlalchemy as sa

from alembic import op
from datetime import datetime
from enum import Enum

# revision identifiers, used by Alembic.
revision = "20190202"
down_revision = "d500457efb3b"
branch_labels = None
depends_on = None


class NewAssignmentActions(Enum):
    release = "release"
    download = "fetch"
    submit = "submit"
    collected = "collected"


class OldAssignmentActions(Enum):
    release = "release"
    download = "fetch"
    submit = "submit"


def upgrade():

    with op.batch_alter_table("action") as batch_op:

        batch_op.alter_column(
            "action",
            "action",
            existing_type=sa.Enum(OldAssignmentActions, name="assignmentactions"),
            type_=sa.Enum(NewAssignmentActions, name="assignmentactions"),
        )


def downgrade():

    with op.batch_alter_table("action") as batch_op:
        batch_op.alter_column(
            "action",
            "action",
            existing_type=sa.Enum(NewAssignmentActions, name="assignmentactions"),
            type_=sa.Enum(OldAssignmentActions, name="assignmentactions"),
        )
