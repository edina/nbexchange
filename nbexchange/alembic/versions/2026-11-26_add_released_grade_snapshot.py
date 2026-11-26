"""Persist the immutable grade alongside each feedback release.

Revision ID: 2026112601
Revises: 2026091501
"""

import sqlalchemy as sa
from alembic import op

revision = "2026112601"
down_revision = "2026091501"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("grade_event_outbox", sa.Column("source_sequence", sa.BigInteger(), nullable=True))
    op.add_column("grade_event_outbox", sa.Column("released_grade", sa.JSON(), nullable=True))
    op.add_column("feedback_2", sa.Column("grade_revision", sa.Unicode(64), nullable=True))


def downgrade():
    op.drop_column("feedback_2", "grade_revision")
    op.drop_column("grade_event_outbox", "released_grade")
    op.drop_column("grade_event_outbox", "source_sequence")
