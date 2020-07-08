import enum
from datetime import datetime

from sqlalchemy import Column, Integer, ForeignKey, Enum, Unicode, DateTime
from sqlalchemy.orm import relationship

from nbexchange.models import Base


# This is the action: a user does something with an assignment, at a given time
class AssignmentActions(enum.Enum):
    released = "released"
    fetched = "fetched"
    submitted = "submitted"
    removed = "removed"
    collected = "collected"


class Action(Base):
    """ Table to map multiple users to a single assignment

    # assume some main objects
    usr = User(hubuser_id = self.get_current_user().id
               username = self.get_current_user().username
              )
    ass = Assignment(assignment_code='test%201')

    # create a new action
    acc = Action(action='fetch')

    # Linking, specifying IDs
    acc.user_id = self.get_current_user().id
    acc.assignment_id = ass.id

    # linking, through appending to lists
    usr.assignments.append(acc)
    ass.users.append(acc)

    # What action have users taken for this Assignment
    for action is ass.users:
      print(f"User {action.user.username} did a {action.action} at {action.timestamp}")

    """

    __tablename__ = "action"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True)
    assignment_id = Column(
        Integer, ForeignKey("assignment.id", ondelete="CASCADE"), index=True
    )
    action = Column(Enum(AssignmentActions), nullable=False, index=True)
    location = Column(
        Unicode(200), nullable=True
    )  # Location for the file of this action
    checksum = Column(Unicode(200), nullable=True)  # Checksum for the saved file
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)

    # These are the relationship handles: a specific subscription has a single user to a single course
    user = relationship("User", back_populates="actions")
    assignment = relationship("Assignment", back_populates="actions")

    def __repr__(self):
        return f"Assignment #{self.assignment_id} {self.action} by {self.user_id} at {self.timestamp}"
