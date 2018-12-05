"""sqlalchemy ORM tools for the state of the constellation of processes"""

# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.
from uuid import uuid4

import alembic.config
import alembic.command
import enum
import json
import os

from alembic.script import ScriptDirectory
from datetime import datetime, timedelta

from sqlalchemy import (
    Boolean,
    Column,
    create_engine,
    DateTime,
    Enum,
    event,
    exc,
    ForeignKey,
    inspect,
    Integer,
    or_,
    select,
    Table,
    Unicode,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.interfaces import PoolListener
from sqlalchemy.orm import (
    interfaces,
    object_session,
    relationship,
    Session,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool
from sqlalchemy.sql.expression import bindparam
from sqlalchemy.types import TypeDecorator, TEXT, LargeBinary
from tornado.log import app_log

# top-level variable for easier mocking in tests
utcnow = datetime.utcnow

Base = declarative_base()

# The keys for the enum match the hard-coded values used by nbgrader in their code
class AssignmentActions(enum.Enum):
    released = "released"
    fetched = "fetched"
    submitted = "submitted"
    removed = "removed"


# This is the action: a user does something with an assignment, at a given time
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
      print("User {} did a {} at {}".format(action.user.username, action.action, action.timestamp)
    
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
    )  # Loction for the file of this action
    timestamp = Column(DateTime, default=datetime.utcnow)

    # These are the relationship handles: a specific subscription has a single user to a single course
    user = relationship("User", back_populates="actions")
    assignment = relationship("Assignment", back_populates="actions")

    def __repr__(self):
        return "Assignment #{} {} by {} at {}".format(
            self.assignment_id, self.action, self.user_id, self.timestamp
        )


# This is the subscription: a user on a course, with a role
class Subscription(Base):
    """ Table to map multiple users to a single course

    # assume some main objects
    usr = User(hubuser_id = self.get_current_user().id
               username = self.get_current_user().username
              )
    crs = Course(org_id=1, course_code=$couurse_code)
 
    # create a new subscription, hard-coded linking
    subscr = Subscription(role='Student', user_id = usr.id)
    subscr.course_id = crs.id
    
    # What action have users taken for this Assignment
    for action is ass.users:
      print("User {} did a {} at {}".format(action.user.username, action.action, action.timestamp)
    """

    __tablename__ = "subscription"
    __table_args__ = (UniqueConstraint("user_id", "course_id", "role"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True)
    course_id = Column(Integer, ForeignKey("course.id", ondelete="CASCADE"), index=True)
    role = Column(Unicode(50), nullable=False)

    # These are the relationship handles: a specific subscription has a single user to a single course
    user = relationship("User", back_populates="courses")
    course = relationship("Course", back_populates="subscribers")

    @classmethod
    def find_by_pk(cls, db, pk, log=None):
        """Find a subscription by Primary Key.
        Returns None if not found.
        """
        if log:
            log.info("Subscription.find_by_pk - pk:{}".format(pk))
        if pk is None:
            raise ValueError("Primary Key needs to be defined")
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
            log.info(
                "Subscription.find_by_set - user_id:{}, course_id:{}, role:{}".format(
                    user_id, course_id, role
                )
            )
        return (
            db.query(cls)
            .filter(
                cls.user_id == user_id, cls.course_id == course_id, cls.role == role
            )
            .first()
        )

    def __repr__(self):
        return "Subscription for user {} to course {} as a {}".format(
            self.user_id, self.course_id, self.role
        )


class User(Base):
    """ The user.

    Note - we don't use the Jupyterhub user, as trying to integratte with the central DB is a pain

    crs = Course(org_id=1, course_code=$couurse_code)
    ass = Assignment(assignment_code='test%201')

    usr = User( name = self.get_current_user().get('name') )
    user.courses.append(crs)
    user.assignments.append(ass)


    # What action have users taken for this Assignment
    for action is user.assignments:
      print("User {} did a {} at {} on assignment {} ".format(user.username,
       action.action, action.timestamp, action.assignment.assignment_code)
    """

    __tablename__ = "user"
    __table_args__ = (UniqueConstraint("name", "org_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
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
        """Find a course by Primary Key.
        Returns None if not found.
        """
        if log:
            log.info("User.find_by_pk - pk:{}".format(pk))

        if pk is None:
            raise ValueError("Primary Key needs to be defined")
        if isinstance(pk, int):
            return db.query(cls).filter(cls.id == pk).first()
        else:
            raise TypeError(f"Primary Keys are required to be Ints")

    @classmethod
    def find_by_name(cls, db, name, log=None):
        """Find a user by name.
        Returns None if not found.
        """
        if log:
            log.info("User.find_by_name - name:{}".format(name))
        if name is None:
            raise ValueError("Name needs to be defined")
        return db.query(cls).filter(cls.name == name).first()

    @classmethod
    def find_by_org(cls, db, org_id, log=None):
        """Find all users for an organisation.
        Returns None if not found.
        """
        if log:
            log.info("User.find_by_org - id:{}".format(org_id))
        org_id = int(float(org_id)) if org_id else None
        if org_id is None:
            raise ValueError("org_id needs to be defined, and a number")
        return list(db.query(cls).filter(cls.org_id == org_id))

    def __repr__(self):
        return "User/{}".format(self.name)


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
            log.info("Course.find_by_pk - pk:{}".format(pk))
        if pk is None:
            raise ValueError("Primary Key needs to be defined")
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
            log.info("Course.find_by_code - code:{} (org_id:{})".format(code, org_id))
        if code is None:
            raise ValueError("code needs to be defined")
        org_id = int(float(org_id)) if org_id else None
        if org_id is None:
            raise ValueError("org_id needs to be defined, and a number")
        return (
            db.query(cls).filter(cls.course_code == code, cls.org_id == org_id).first()
        )

    @classmethod
    def find_by_org(cls, db, org_id, log=None):
        """Find all courses or an organisation.
        Returns None if not found.
        """
        if log:
            log.info("Course.find_by_org - id:{}".format(org_id))
        org_id = int(float(org_id)) if org_id else None
        if org_id is None:
            raise ValueError("org_id needs to be defined, and a number")
        return list(db.query(cls).filter(cls.org_id == org_id))

    def __repr__(self):
        return "Course/{} {}".format(self.course_code, self.course_title)


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

    for action is ass.users:
      print("User {} did a {} at {}".format(action.user.username, action.action, action.timestamp)
    
    """

    __tablename__ = "assignment"
    __table_args__ = (UniqueConstraint("course_id", "assignment_code", "active"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    assignment_code = Column(Unicode(50), nullable=False, index=True)
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
            log.info("Assignmetn.find_by_pk - pk:{}".format(pk))
        if pk is None:
            raise ValueError("Primary Key needs to be defined")
        if isinstance(pk, int):
            return db.query(cls).filter(cls.id == pk).first()
        else:
            raise TypeError(f"Primary Keys are required to be Ints")

    @classmethod
    def find_by_code(cls, db, code, course_id=None, active=True, log=None):
        """Find an assignment by code.
        Returns None if not found.
        """
        if log:
            log.info(
                "Assignment.find_by_code - code:{} (course_id:{}, active:{})".format(
                    code, course_id, active
                )
            )
        if code is None:
            raise ValueError("code needs to be defined")
        if course_id and not isinstance(course_id, int):
            raise TypeError(f"Course_id, if specified, must be an Int")
        return (
            db.query(cls)
            .filter(
                cls.assignment_code == code,
                cls.course_id == course_id,
                cls.active == active,
            )
            .order_by(cls.id.desc())
            .first()
        )

    @classmethod
    def find_for_course(cls, db, course_id, active=True, log=None):
        """Find the list of assignments for a course.
    Returns None if not found.
    """
        if log:
            log.info(
                "Assignment.find_for_course - course_id:{}, active:{}".format(
                    course_id, active
                )
            )
        return db.query(cls).filter(cls.course_id == course_id, cls.active == active)

    def __repr__(self):
        return "Assignment {} for course {}".format(
            self.assignment_code, self.course_id
        )


class Notebook(Base):

    __tablename__ = "notebook"
    __table_args__ = (UniqueConstraint("name", "assignment_id"),)

    #: Unique id of the notebook (automatically incremented)
    id = Column(Integer(), primary_key=True, autoincrement=True)

    #: Unique human-readable name for the notebook, such as "Problem 1". Note
    #: the uniqueness is only constrained within assignments (e.g. it is ok for
    #: two different assignments to both have notebooks called "Problem 1", but
    #: the same assignment cannot have two notebooks with the same name).
    name = Column(Unicode(128), nullable=False)

    assignment = None
    #: Unique id of :attr:`~nbexchange.orm.Notebook.assignment`
    assignment_id = Column(Integer(), ForeignKey("assignment.id"))

    def __repr__(self):
        return "Notebook<{}/{}>".format(self.assignment.name, self.name)


### ref: https://docs.sqlalchemy.org/en/latest/orm/basic_relationships.html


# General database utilities


class DatabaseSchemaMismatch(Exception):
    """Exception raised when the database schema version does not match

    the current version of NbExchange.
    """


class ForeignKeysListener(PoolListener):
    """Enable foreign keys on sqlite"""

    def connect(self, dbapi_con, con_record):
        dbapi_con.execute("pragma foreign_keys=ON")


def _expire_relationship(target, relationship_prop):
    """Expire relationship backrefs

    used when an object with relationships is deleted
    """

    session = object_session(target)
    # get peer objects to be expired
    peers = getattr(target, relationship_prop.key)
    if peers is None:
        # no peer to clear
        return
    # many-to-many and one-to-many have a list of peers
    # many-to-one has only one
    if relationship_prop.direction is interfaces.MANYTOONE:
        peers = [peers]
    for obj in peers:
        if inspect(obj).persistent:
            session.expire(obj, [relationship_prop.back_populates])


@event.listens_for(Session, "persistent_to_deleted")
def _notify_deleted_relationships(session, obj):
    """Expire relationships when an object becomes deleted

    Needed to keep relationships up to date.
    """
    mapper = inspect(obj).mapper
    for prop in mapper.relationships:
        if prop.back_populates:
            _expire_relationship(obj, prop)


def register_ping_connection(engine):
    """Check connections before using them.

    Avoids database errors when using stale connections.nbexchange.sqlite

    From SQLAlchemy docs on pessimistic disconnect handling:

    https://docs.sqlalchemy.org/en/rel_1_1/core/pooling.html#disconnect-handling-pessimistic
    """

    @event.listens_for(engine, "engine_connect")
    def ping_connection(connection, branch):
        if branch:
            # "branch" refers to a sub-connection of a connection,
            # we don't want to bother pinging on these.
            return

        # turn off "close with result".  This flag is only used with
        # "connectionless" execution, otherwise will be False in any case
        save_should_close_with_result = connection.should_close_with_result
        connection.should_close_with_result = False

        try:
            # run a SELECT 1.   use a core select() so that
            # the SELECT of a scalar value without a table is
            # appropriately formatted for the backend
            connection.scalar(select([1]))
        except exc.DBAPIError as err:
            # catch SQLAlchemy's DBAPIError, which is a wrapper
            # for the DBAPI's exception.  It includes a .connection_invalidated
            # attribute which specifies if this connection is a "disconnect"
            # condition, which is based on inspection of the original exception
            # by the dialect in use.
            if err.connection_invalidated:
                # app_log.error("Database connection error, attempting to reconnect: %s", err)
                # run the same SELECT again - the connection will re-validate
                # itself and establish a new connection.  The disconnect detection
                # here also causes the whole connection pool to be invalidated
                # so that all stale connections are discarded.
                connection.scalar(select([1]))
            else:
                raise
        finally:
            # restore "close with result"
            connection.should_close_with_result = save_should_close_with_result


def check_db_revision(engine, log=None):
    """Check the NbExchange database revision

    After calling this function, an alembic tag is guaranteed to be stored in the db.

    - Checks the alembic tag and raises a ValueError if it's not the current revision
    - If no tag is stored (Bug in Hub prior to 0.8),
      guess revision based on db contents and tag the revision.
    - Empty databases are tagged with the current revision
    """

    # Check database schema version
    current_table_names = set(engine.table_names())
    my_table_names = set(Base.metadata.tables.keys())

    from nbexchange.dbutil import _temp_alembic_ini

    with _temp_alembic_ini(engine.url) as ini:
        cfg = alembic.config.Config(ini)
        scripts = ScriptDirectory.from_config(cfg)
        head = scripts.get_heads()[0]
        base = scripts.get_base()

        if not my_table_names.intersection(current_table_names):
            # no tables have been created, stamp with current revision
            log.info("Stamping empty database with alembic revision %s", head)
            alembic.command.stamp(cfg, head)
            return

    # check database schema version
    # it should always be defined at this point
    alembic_revision = engine.execute(
        "SELECT version_num FROM alembic_version"
    ).first()[0]
    if alembic_revision == head:
        log.debug("database schema version found: %s", alembic_revision)
        pass
    else:
        raise DatabaseSchemaMismatch(
            "Found database schema version {found} != {head}. "
            "Backup your database and run `jupyterhub upgrade-db`"
            " to upgrade to the latest schema.".format(
                found=alembic_revision, head=head
            )
        )


def mysql_large_prefix_check(engine):
    """Check mysql has innodb_large_prefix set"""
    if not str(engine.url).startswith("mysql"):
        return False
    variables = dict(
        engine.execute(
            "show variables where variable_name like "
            '"innodb_large_prefix" or '
            'variable_name like "innodb_file_format";'
        ).fetchall()
    )
    if (
        variables["innodb_file_format"] == "Barracuda"
        and variables["innodb_large_prefix"] == "ON"
    ):
        return True
    else:
        return False


def add_row_format(base):
    for t in base.metadata.tables.values():
        t.dialect_kwargs["mysql_ROW_FORMAT"] = "DYNAMIC"


def new_session_factory(
    url="sqlite:///:memory:", reset=False, expire_on_commit=False, log=None, **kwargs
):
    """Create a new session at url"""
    log.info("orm.new_session_factory: db_url:{}, reset:{}".format(url, reset))
    if url.startswith("sqlite"):
        kwargs.setdefault("connect_args", {"check_same_thread": False})
        listeners = kwargs.setdefault("listeners", [])
        listeners.append(ForeignKeysListener())

    elif url.startswith("mysql"):
        kwargs.setdefault("pool_recycle", 60)

    if url.endswith(":memory:"):
        # If we're using an in-memory database, ensure that only one connection
        # is ever created.
        kwargs.setdefault("poolclass", StaticPool)

    engine = create_engine(url, **kwargs)
    log.info("orm.new_session_factory: engine:{}".format(engine))
    # enable pessimistic disconnect handling
    register_ping_connection(engine)

    if reset:
        Base.metadata.drop_all(engine)

    if mysql_large_prefix_check(engine):  # if mysql is allows large indexes
        add_row_format(Base)  # set format on the tables
    # check the db revision (will raise, pointing to `upgrade-db` if version doesn't match)
    check_db_revision(engine, log)

    Base.metadata.create_all(engine)

    # We set expire_on_commit=False, since we don't actually need
    # SQLAlchemy to expire objects after committing - we don't expect
    # concurrent runs of the hub talking to the same db. Turning
    # this off gives us a major performance boost
    session_factory = sessionmaker(bind=engine, expire_on_commit=expire_on_commit)
    return session_factory
