from sqlalchemy import UniqueConstraint, Column, Integer, Unicode
from sqlalchemy.orm import relationship

from nbexchange.models import Base


class Course(Base):
    """ The list of courses we know, who's subscribed to them, and what
    assignments have been have been issued for each course

    crs = Course(org_id=1, course_code=$couurse_code, course_title=$optional_human_readable_title)
    sub = Subscription(role = 'Instructor')
    sub.user_id = self.get_current_user().id
    crs.subscribers.append(sub)


    ass = Assignment(assignment_code='test%201')
    crs.assignments.append(ass)
    """

    __tablename__ = "course"
    __table_args__ = (UniqueConstraint("course_code", "org_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, nullable=False, index=True)
    course_code = Column(Unicode(200), nullable=False, index=True)
    course_title = Column(Unicode(200), nullable=True, index=True)

    ## course <-> user relationship
    # One to Many. One Course to many users. Each relationship has additional data
    subscribers = relationship("Subscription", back_populates="course")

    ## course <-> assignment relationship
    # One to Many. One Course, many assignments. Can set assignmnt.course
    assignments = relationship("Assignment", back_populates="course")

    @classmethod
    def find_by_pk(cls, db, pk, log=None):
        """Find a course by Primary Key.
        Returns None if not found.
        """
        if log:
            log.info(f"Course.find_by_pk - pk:{pk}")
        if pk is None:
            raise ValueError(f"Primary Key needs to be defined")
        if isinstance(pk, int):
            return db.query(cls).filter(cls.id == pk).first()
        else:
            raise TypeError(f"Primary Keys are required to be Ints")

    @classmethod
    def find_by_code(cls, db, code, org_id, log=None):
        """Find a course by name.
        Returns None if not found.
        """
        if log:
            log.info(f"Course.find_by_code - code:{code} (org_id:{org_id})")
        if code is None:
            raise ValueError(f"code needs to be defined")
        org_id = int(float(org_id)) if org_id else None
        if org_id is None:
            raise ValueError(f"org_id needs to be defined, and a number")
        return (
            db.query(cls).filter(cls.course_code == code, cls.org_id == org_id).first()
        )

    @classmethod
    def find_by_org(cls, db, org_id, log=None):
        """Find all courses or an organisation.
        Returns None if not found.
        """
        if log:
            log.info(f"Course.find_by_org - id:{org_id}")
        org_id = int(float(org_id)) if org_id else None
        if org_id is None:
            raise ValueError(f"org_id needs to be defined, and a number")
        return list(db.query(cls).filter(cls.org_id == org_id))

    def __repr__(self):
        return f"Course/{self.course_code} {self.course_title}"
