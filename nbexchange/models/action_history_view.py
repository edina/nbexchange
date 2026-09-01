"""View model for optimized action history queries."""

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text

from nbexchange.models import Base
from nbexchange.models.actions import AssignmentActions


class ActionHistoryView(Base):
    """Read-only view for action history queries.

    This denormalizes the relationship between subscriptions, courses,
    assignments, and actions into a single queryable table.

    Note: This is a database VIEW, not a physical table. It cannot be
    used for INSERT/UPDATE/DELETE operations.
    """

    __tablename__ = "v_action_history"
    __table_args__ = {
        "include_columns": [
            "viewer_user_id",
            "course_id",
            "course_code",
            "course_title",
            "viewer_role",
            "assignment_id",
            "assignment_code",
            "assignment_active",
            "action_id",
            "action",
            "location",
            "timestamp",
            "actor_user_id",
            "actor_name",
        ]
    }

    viewer_user_id = Column(Integer, primary_key=True)
    course_id = Column(Integer, primary_key=True)
    course_code = Column(String(200))
    course_title = Column(String(200))
    viewer_role = Column(String)

    assignment_id = Column(Integer, primary_key=True)
    assignment_code = Column(Text)
    assignment_active = Column(Boolean)

    action_id = Column(Integer, primary_key=True)
    action = Column(Enum(AssignmentActions), index=True)
    location = Column(String(200))
    timestamp = Column(DateTime(timezone=True))
    actor_user_id = Column(Integer)
    actor_name = Column(String)

    def __repr__(self):
        return (
            f"<ActionHistoryView course={self.course_code} " f"assignment={self.assignment_code} action={self.action}>"
        )
