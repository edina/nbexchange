"""Add indexes used by the lazy history endpoints.

Revision ID: 2026082101
Revises: 2026041701
Create Date: 2026-08-21
"""

from alembic import op

revision = "2026082101"
down_revision = "2026041701"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_subscription_user_course",
        "subscription",
        ["user_id", "course_id"],
    )
    op.create_index(
        "ix_assignment_course_active",
        "assignment",
        ["course_id", "active", "id"],
    )
    op.create_index(
        "ix_action_assignment_history",
        "action",
        ["assignment_id", "timestamp", "id"],
    )


def downgrade():
    op.drop_index("ix_action_assignment_history", table_name="action")
    op.drop_index("ix_assignment_course_active", table_name="assignment")
    op.drop_index("ix_subscription_user_course", table_name="subscription")
