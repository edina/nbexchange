"""Add item to Action Enum table 

Revision ID: d500457efb3b
Revises: 9794df114fd9
Create Date: 2018-10-29 16:08:09.549850

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
    op.alter_column(
        "action", "action", type_= sa.Enum(NewAssignmentActions), nullable=False, index=True
    )

def downgrade():
    op.alter_column(
        "action", "action", type_= sa.Enum(OldAssignmentActions), nullable=False, index=True
    )