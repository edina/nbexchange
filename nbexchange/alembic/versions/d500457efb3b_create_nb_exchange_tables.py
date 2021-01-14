"""create NB Exchange tables

Revision ID: d500457efb3b
Revises: 9794df114fd9
Create Date: 2018-10-29 16:08:09.549850

"""
from datetime import datetime
from enum import Enum

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d500457efb3b"
down_revision = "9794df114fd9"
branch_labels = None
depends_on = None


class AssignmentActions(Enum):
    release = "release"
    download = "fetch"
    submit = "submit"


def upgrade():

    # Users.
    # Need to be separated by some kind of organisational ID
    op.create_table(
        "user",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, nullable=False, index=True),
        sa.Column(
            "hubuser_id", sa.Integer, nullable=False, index=True
        ),  # code from jupyterhub
        sa.Column("username", sa.Unicode(200), nullable=False, index=True),
    )
    op.create_unique_constraint("uq_users", "user", ["username", "org_id"])

    # Courses.
    # Need to be separated by some kind of organisational ID
    op.create_table(
        "course",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("org_id", sa.Integer, nullable=False, index=True),
        sa.Column("course_code", sa.Unicode(200), nullable=False, index=True),
    )
<<<<<<< HEAD
    op.create_unique_constraint("uq_courses", "course", ["course_code", "org_id"])
=======
    op.create_unique_constraint("uq_courses", 'course"', ["course_code", "org_id"])
>>>>>>> min-work stash to go bug-hunting

    # user -> course_code, with role
    # Unique across all three, however a user can have multiple roles on a course.
    # Role should be `student` or `instructor` - but I'm not ruling out others
    op.create_table(
        "subscription",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False, index=True
        ),
        sa.Column(
            "course_id",
            sa.Integer,
            sa.ForeignKey("course.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("role", sa.Unicode(50), nullable=False),
    )
    op.create_unique_constraint(
        "uq_subscription", "subscription", ["user_id", "course_id", "role"]
    )

    # assignments for a course - there can be more than one
    # assigment_code is what comes from formgrader
    op.create_table(
        "assignment",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("assignment_code", sa.Unicode(50), nullable=False, index=True),
        sa.Column("active", sa.Boolean, default=True, nullable=False),
        sa.Column(
            "course_id",
            sa.Integer,
            sa.ForeignKey("course.id"),
            nullable=False,
            index=True,
        ),
    )

    # Keeping a track of when assignments are pulled/posted
    op.create_table(
        "action",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "user_id", sa.Integer, sa.ForeignKey("user.id"), nullable=False, index=True
        ),
        sa.Column(
            "assignment_id",
            sa.Integer,
            sa.ForeignKey("assignment.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "action", sa.Enum(AssignmentActions), nullable=False, index=True
        ),  # constrain to 'release', 'download', 'submit'
        sa.Column("timestamp", sa.DateTime, server_default=datetime.utcnow),
    )


def downgrade():
    op.drop_table("action")
    op.drop_table("assignment")
    op.drop_table("subscription")
    op.drop_table("course")
    op.drop_table("user")
