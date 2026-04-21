"""Ensure all timestamps are timezone aware

At the time this migration was created, this is the state across three databases:

developer-environment:
- action.timestamp : TIMESTAMP WITH TIMEZONE
- feedback_2.timestamp : TIMESTAMP WITH TIMEZONE
- feedback_2.created_at : TIMESTAMP WITH TIMEZONE

dev:
- action.timestamp : TIMESTAMP WITH TIMEZONE
- feedback_2.timestamp : TIMESTAMP WITH TIMEZONE
- feedback_2.created_at : TIMESTAMP WITH TIMEZONE

beta:
- action.timestamp : TIMESTAMP WITHOUT TIMEZONE
- feedback_2.timestamp : TIMESTAMP WITH TIMEZONE
- feedback_2.created_at : TIMESTAMP WITH TIMEZONE

prod:
- action.timestamp : TIMESTAMP WITHOUT TIMEZONE
- feedback_2.timestamp : TIMESTAMP WITH TIMEZONE
- feedback_2.created_at : TIMESTAMP WITH TIMEZONE

Revision ID: 2026041701
Revises: 2024093001
Create Date: 2026-04-17 08:25

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = "2026041701"
down_revision = "2024093001"
branch_labels = None
depends_on = None


def upgrade():

    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)

    # Get existing type of the column from metadata
    columns = inspector.get_columns("action")
    column_type = next((col["type"] for col in columns if col["name"] == "timestamp"), None)

    # Check if the current type is TIMESTAMP WITHOUT TIMEZONE
    if isinstance(column_type, sa.TIMESTAMP) and not column_type.timezone:
        op.execute("""
            ALTER TABLE action
            ALTER COLUMN timestamp
            TYPE TIMESTAMP WITH TIME ZONE
            USING timestamp AT TIME ZONE 'UTC'
        """)
    else:
        raise Exception("Migration aborted: the column type is not TIMESTAMP WITHOUT TIMEZONE")


def downgrade():
    pass
