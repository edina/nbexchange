"""Add a history 'View' table to the database.

Revision ID: 2026041701
Revises: 2026041701
Create Date: 2026-04-17 08:25

"""

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "2026082501"
down_revision = "2026041701"
branch_labels = None
depends_on = None


def upgrade():
    view_sql = """
    CREATE VIEW v_action_history AS
    SELECT
        s.user_id AS viewer_user_id,
        s.course_id,
        c.course_code,
        c.course_title,
        s.role AS viewer_role,
        a.id AS assignment_id,
        a.assignment_code,
        a.active AS assignment_active,
        act.id AS action_id,
        act.action,
        act.location,
        act.timestamp,
        act.user_id AS actor_user_id,
        u.name AS actor_name
    FROM subscription s
    JOIN course c ON c.id = s.course_id
    JOIN assignment a ON a.course_id = c.id AND a.active = true
    JOIN action act ON act.assignment_id = a.id
    JOIN user u ON u.id = act.user_id
    ORDER BY s.user_id, s.course_id, a.id, act.id
    """
    op.execute(text(view_sql))


def downgrade():
    op.execute(text("DROP VIEW IF EXISTS v_action_history"))
