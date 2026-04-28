"""Ensure all timestamps are timezone aware

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
        pass


def downgrade():
    pass
