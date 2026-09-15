"""Add durable grade-ready event outbox.

Revision ID: 2026091501
Revises: 2026082101
Create Date: 2026-09-15
"""

import sqlalchemy as sa
from alembic import op

revision = "2026091501"
down_revision = "2026082101"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "grade_event_outbox",
        sa.Column("event_id", sa.Unicode(length=36), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("org_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("course_code", sa.Unicode(length=200), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("assignment_code", sa.Text(), nullable=False),
        sa.Column("learner_id", sa.Integer(), nullable=False),
        sa.Column("learner_name", sa.Unicode(length=200), nullable=False),
        sa.Column("source_revision", sa.Unicode(length=200), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
        sa.UniqueConstraint("source_revision"),
    )
    op.create_index("ix_grade_event_outbox_org_id", "grade_event_outbox", ["org_id"])
    op.create_index("ix_grade_event_outbox_published_at", "grade_event_outbox", ["published_at"])


def downgrade():
    op.drop_index("ix_grade_event_outbox_published_at", table_name="grade_event_outbox")
    op.drop_index("ix_grade_event_outbox_org_id", table_name="grade_event_outbox")
    op.drop_table("grade_event_outbox")
