from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Unicode,
    UnicodeText,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from nbexchange.models import Base


class Subscription(Base):
    """Table to map multiple users to a single course

    # assume some main objects
    usr = User(hubuser_id = self.get_current_user().id
               username = self.get_current_user().username
              )
    crs = Course(org_id=1, course_code=$couurse_code)

    # create a new subscription, hard-coded linking
    subscr = Subscription(role='Student', user_id = usr.id)
    subscr.course_id = crs.id

    """

    __tablename__ = "subscription"
    __table_args__ = (UniqueConstraint("user_id", "course_id", "role"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True)
    course_id = Column(Integer, ForeignKey("course.id", ondelete="CASCADE"), index=True)
    role = Column(UnicodeText, nullable=False)

    # These are the relationship handles: a specific subscription has a single user to a single course
    user = relationship("User", back_populates="courses")
    course = relationship("Course", back_populates="subscribers")

    @classmethod
    def find_by_pk(cls, db, pk, log=None):
        """Find a subscription by Primary Key.
        Returns None if not found.
        """
        if log:
            log.debug(f"Subscription.find_by_pk - pk:{pk}")
        if pk is None:
            raise ValueError(f"Primary Key needs to be defined")
        if isinstance(pk, int):
            return db.query(cls).filter(cls.id == pk).first()
        else:
            raise TypeError(f"Primary Keys are required to be Ints")

    @classmethod
    def find_by_set(cls, db, user_id, course_id, role, log=None):
        """Find a subscription by user, course, and role.
        Returns None if not found.
        """
        if log:
            log.debug(f"Subscription.find_by_set - user_id:{user_id}, course_id:{course_id}, role:{role}")
        return db.query(cls).filter(cls.user_id == user_id, cls.course_id == course_id, cls.role == role).first()

    def __repr__(self):
        return f"Subscription for user {self.user_id} to course {self.course_id} as a {self.role}"
