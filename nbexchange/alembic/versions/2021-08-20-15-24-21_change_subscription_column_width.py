"""Change subscription column width

Revision ID: 2540572282f2
Revises: bfe19408f64f
Create Date: 2021-08-20 15:24:21.878350

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "2540572282f2"
down_revision = "bfe19408f64f"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE subscription ALTER COLUMN role TYPE Text")


def downgrade():
    op.execute("ALTER TABLE subscription ALTER COLUMN role TYPE VARCHAR(50)")
