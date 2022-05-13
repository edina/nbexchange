import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Unicode
from sqlalchemy.orm import relationship

from nbexchange.models import Base


# This is the action: a user does something with an assignment, at a given time
class AssignmentActions(enum.Enum):
    released = "released"
    fetched = "fetched"
    submitted = "submitted"
    removed = "removed"
    collected = "collected"
    feedback_released = "feedback_released"
    feedback_fetched = "feedback_fetched"


class Action(Base):
    """Table to map multiple users to a single assignment

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
    assignment_id = Column(Integer, ForeignKey("assignment.id", ondelete="CASCADE"), index=True)
    action = Column(Enum(AssignmentActions), nullable=False, index=True)
    location = Column(Unicode(200), nullable=True)  # Location for the file of this action
    checksum = Column(Unicode(200), nullable=True)  # Checksum for the saved file
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)

    # These are the relationship handles: a specific subscription has a single user to a single course
    user = relationship("User", back_populates="actions")
    assignment = relationship("Assignment", back_populates="actions")

    def __repr__(self):
        return f"Assignment #{self.assignment_id} {self.action} by {self.user_id} at {self.timestamp}"

    @classmethod
    def find_by_pk(cls, db, pk, log=None):
        """Find an Action by Primary Key.
        Returns None if not found.
        """
        if log:
            log.debug(f"Action.find_by_pk - pk:{pk}")

        if pk is None:
            raise ValueError(f"Primary Key needs to be defined")
        if isinstance(pk, int):
            return db.query(cls).filter(cls.id == pk).first()
        else:
            raise TypeError(f"Primary Keys are required to be Ints")

    @classmethod
    def find_most_recent_action(cls, db, assignment_id, action=None, log=None):
        """Find the most recent action for a given assignment

        action = orm.Action.find_most_recent_action(
            db=session, assignment_id=current_assignment.id,
        )

        optional parameters:
            'action' Allows one to restrict the search to a specific action. Not used
                if set to None. Defaults to None

        Returns None if not found
        """
        if log:
            log.debug(f"Action.find_most_recent_action - code:{assignment_id} (action:{action})")
        if assignment_id is None or not isinstance(assignment_id, int):
            raise TypeError(f"assignment_id must be defined, and an Int")
        if action is not None and not (isinstance(action, str) or isinstance(action, AssignmentActions)):
            raise TypeError(f"action, if defined, must be a string")
        filters = [cls.assignment_id == assignment_id]
        if action:
            filters.append(cls.action == action)
        return db.query(cls).filter(*filters).order_by(cls.id.desc()).first()
