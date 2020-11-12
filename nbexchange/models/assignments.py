from sqlalchemy import (
    UniqueConstraint,
    Column,
    Integer,
    Unicode,
    Boolean,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship

from nbexchange.models.actions import Action
from nbexchange.models import Base


class Assignment(Base):
    """The Assigments known for each course

    There is probably more than 1 assignment for each course
    Tthere will be multiple users interaction with a single assignment - each interaction can have a different "action"

    assigment_code is what comes from formgrader

    crs = Course(org_id=1, course_code=$couurse_code)
    ass = crs.assignments(assignment_code='test%201')
    acc = Action(action='fetch')
    acc.user_id = self.get_current_user().id
    acc.assignment_id = ass.id
    ass.users.append(acc)
    """

    __tablename__ = "assignment"
    __table_args__ = (UniqueConstraint("course_id", "assignment_code", "active"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_code = Column(Text(), nullable=False, index=True)
    active = Column(Boolean, default=True, nullable=False)

    ## course <-> assignment mappings
    # each assignment has just one parent course
    course_id = Column(Integer, ForeignKey("course.id", ondelete="CASCADE"), index=True)
    # can set 'course.assignments'
    course = relationship("Course", back_populates="assignments")

    # Maps this assignment to multiple actions [thence to users]
    actions = relationship("Action", back_populates="assignment")

    # Tracks the notebooks in each assignment
    notebooks = relationship("Notebook", backref="assignment", order_by="Notebook.name")

    @classmethod
    def find_by_pk(cls, db, pk, log=None):
        """Find an Assignment by Primary Key.
        Returns None if not found.
        """
        if log:
            log.debug(f"Assignmetn.find_by_pk - pk:{pk}")
        if pk is None:
            raise ValueError(f"Primary Key needs to be defined")
        if isinstance(pk, int):
            return db.query(cls).filter(cls.id == pk).first()
        else:
            raise TypeError(f"Primary Keys are required to be Ints")

    @classmethod
    def find_by_code(cls, db, code, course_id=None, active=True, log=None, action=None):
        """Find an assignment by code.

        assignment = orm.Assignment.find_by_code(
            db=session, code=assignment_code, course_id=course.id
        )

        optional params:
            'active' True/False - defaults to true
            'action' Allows one to restrict the search to a specific action. Not used
                if set to None. Defaults to None

        Returns None if not found.
        """
        if log:
            log.debug(
                f"Assignment.find_by_code - code:{code} (course_id:{course_id}, active:{active}, action:{action})"
            )
        if code is None:
            raise ValueError(f"code needs to be defined")
        if course_id and not isinstance(course_id, int):
            raise TypeError(f"Course_id, if specified, must be an Int")
        filters = [
            cls.assignment_code == code,
            cls.course_id == course_id,
            cls.active == active,
        ]
        if action:
            filters.append(cls.actions.any(Action.action == action))
        return db.query(cls).filter(*filters).order_by(cls.id.desc()).first()

    @classmethod
    def find_for_course(
        cls, db, course_id, active=True, log=None, action=None, path=None
    ):
        """Find the list of assignments for a course.

        assignments = orm.Assignment.find_for_course(
            db=session, course_id=course.id, log=self.log
        )

        optional params:
            'active' True/False - defaults to true
            'action' Allows one to restrict the search to a specific action. Not used
                if set to None. Defaults to None
            'path' Allows one to restrict the search to a specific location [path] in an action.
                Not used if set to None. Defaults to None

        Returns None if not found.
        """
        if log:
            log.debug(
                f"Assignment.find_for_course - course_id:{course_id}, active:{active}, action:{action}"
            )

        if course_id and not isinstance(course_id, int):
            raise TypeError(f"Course_id, if specified, must be an Int")
        filters = [cls.course_id == course_id, cls.active == active]
        if action:
            filters.append(cls.actions.any(Action.action == action))
        if path:
            filters.append(cls.actions.any(Action.location == path))
        return db.query(cls).filter(*filters).order_by(cls.id.desc())

    def __repr__(self):
        return f"Assignment {self.assignment_code} for course {self.course_id}"
