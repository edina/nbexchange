from sqlalchemy import UniqueConstraint, Column, Integer, Unicode
from sqlalchemy.orm import relationship

from nbexchange.models import Base


class User(Base):
    """The user.

    Note - we don't use the Jupyterhub user, as trying to integratte with the central DB is a pain

    crs = Course(org_id=1, course_code=$couurse_code)
    ass = Assignment(assignment_code='test%201')

    usr = User( name = self.get_current_user().get('name') )
    user.courses.append(crs)
    user.assignments.append(ass)
    """

    __tablename__ = "user"
    __table_args__ = (UniqueConstraint("name", "org_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    # External ID
    ext_id = Column(Integer, index=True, unique=True)
    name = Column(Unicode(200), nullable=False, index=True)
    org_id = Column(Integer, nullable=False, index=True)

    ## User <-> Course Relationship
    # One to Many. One user has multiple courses
    courses = relationship("Subscription", back_populates="user")

    # ## User <-> Assignments Relationship
    # # One to Many. One user has multiple assignments
    actions = relationship("Action", back_populates="user")

    @classmethod
    def find_by_pk(cls, db, pk, log=None):
        """Find a user by Primary Key.
        Returns None if not found.
        """
        if log:
            log.debug(f"User.find_by_pk - pk:{pk}")

        if pk is None:
            raise ValueError(f"Primary Key needs to be defined")
        if isinstance(pk, int):
            return db.query(cls).filter(cls.id == pk).first()
        else:
            raise TypeError(f"Primary Keys are required to be Ints")

    @classmethod
    def find_by_ext_id(cls, db, ext_id, log=None):
        """Find a user by Primary Key.
        Returns None if not found.
        """
        if log:
            log.debug(f"User.find_by_ext_id - ext_id:{ext_id}")

        if ext_id is None:
            raise ValueError(f"External key needs to be defined")
        if isinstance(ext_id, int):
            return db.query(cls).filter(cls.ext_id == ext_id).first()
        else:
            raise TypeError(f"External IDs are required to be Ints")

    @classmethod
    def find_by_name(cls, db, name, log=None):
        """Find a user by name.
        Returns None if not found.
        """
        if log:
            log.debug(f"User.find_by_name - name:{name}")
        if name is None:
            raise ValueError(f"Name needs to be defined")
        return db.query(cls).filter(cls.name == name).first()

    @classmethod
    def find_by_org(cls, db, org_id, log=None):
        """Find all users for an organisation.
        Returns None if not found.
        """
        if log:
            log.debug(f"User.find_by_org - id:{org_id}")
        org_id = int(float(org_id)) if org_id else None
        if org_id is None:
            raise ValueError(f"org_id needs to be defined, and a number")
        return list(db.query(cls).filter(cls.org_id == org_id))

    def __repr__(self):
        return f"User/{self.name}"
