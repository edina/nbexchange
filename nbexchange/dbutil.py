"""Database utilities for NbExchange"""
# Completely derived from the Jupyterhub code!!
import os
import shutil
import sys
from contextlib import contextmanager
from datetime import datetime
from subprocess import check_call
from tempfile import TemporaryDirectory

import alembic.command
import alembic.config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, exc, inspect, select
from sqlalchemy.orm import Session, interfaces, object_session
from sqlalchemy.pool import StaticPool

from nbexchange.models import Base

_here = os.path.abspath(os.path.dirname(__file__))

ALEMBIC_INI_TEMPLATE_PATH = os.path.join(_here, "alembic.ini")
ALEMBIC_DIR = os.path.join(_here, "alembic")


def write_alembic_ini(alembic_ini="alembic.ini", db_url="sqlite:///nbexchange.sqlite"):
    """Write a complete alembic.ini from our template.

    Parameters
    ----------

    alembic_ini: str
        path to the alembic.ini file that should be written.
    db_url: str
        The SQLAlchemy database url, e.g. `sqlite:///nbexchange.sqlite`.
    """
    with open(ALEMBIC_INI_TEMPLATE_PATH) as f:
        alembic_ini_tpl = f.read()

    with open(alembic_ini, "w") as f:
        f.write(
            alembic_ini_tpl.format(
                alembic_dir=ALEMBIC_DIR,
                # If there are any %s in the URL, they should be replaced with %%, since ConfigParser
                # by default uses %() for substitution. You'll get %s in your URL when you have usernames
                # with special chars (such as '@') that need to be URL encoded. URL Encoding is done with %s.
                # YAY for nested templates?
                db_url=str(db_url).replace("%", "%%"),
            )
        )


@contextmanager
def _temp_alembic_ini(db_url):
    """Context manager for temporary nbexchange alembic directory

    Temporarily write an alembic.ini file for use with alembic migration scripts.

    Context manager yields alembic.ini path.

    Parameters
    ----------

    db_url: str
        The SQLAlchemy database url, e.g. `sqlite:///nbexchange.sqlite`.

    Returns
    -------

    alembic_ini: str
        The path to the temporary alembic.ini that we have created.
        This file will be cleaned up on exit from the context manager.
    """
    with TemporaryDirectory() as td:
        alembic_ini = os.path.join(td, "alembic.ini")
        write_alembic_ini(alembic_ini, db_url)
        yield alembic_ini


def upgrade(db_url, revision="head"):
    """Upgrade the given database to revision.

    db_url: str
        The SQLAlchemy database url, e.g. `sqlite:///nbexchange.sqlite`.
    revision: str [default: head]
        The alembic revision to upgrade to.
    """
    with _temp_alembic_ini(db_url) as alembic_ini:
        check_call(["alembic", "-c", alembic_ini, "upgrade", revision])


def backup_db_file(db_file, log=None):
    """Backup a database file if it exists"""
    timestamp = datetime.now().strftime(".%Y-%m-%d-%H%M%S")
    backup_db_file = db_file + timestamp
    for i in range(1, 10):
        if not os.path.exists(backup_db_file):
            break
        backup_db_file = f"{db_file}.{timestamp}.{i}"

    if os.path.exists(backup_db_file):
        raise OSError(f"backup db file already exists: {backup_db_file}")
    if log:
        log.info(f"Backing up {db_file} => {backup_db_file}")
    shutil.copy(db_file, backup_db_file)


def upgrade_if_needed(db_url, backup=True, log=None):
    """Upgrade a database if needed

    If the database is sqlite, a backup file will be created with a timestamp.
    Other database systems should perform their own backups prior to calling this.
    """
    # run check-db-revision first
    engine = create_engine(db_url)

    try:
        check_db_revision(engine, log)
    except DatabaseSchemaMismatch:
        # ignore mismatch error because that's what we are here for!
        pass
    else:
        # nothing to do
        return
    log.info(f"Upgrading {db_url}")
    # we need to upgrade, backup the database
    if backup and db_url.startswith("sqlite:///"):
        db_file = db_url.split(":///", 1)[1]
        backup_db_file(db_file, log=log)
    upgrade(db_url)


def _alembic(args):
    """Run an alembic command with a temporary alembic.ini"""
    from nbexchange.app import NbExchange

    hub = NbExchange()
    hub.load_config_file(hub.config_file)
    db_url = hub.db_url
    with _temp_alembic_ini(db_url) as alembic_ini:
        check_call(["alembic", "-c", alembic_ini] + args)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    # dumb option parsing, since we want to pass things through
    # to subcommands
    choices = ["alembic"]
    if not args or args[0] not in choices:
        print("Select a command from: %s" % ", ".join(choices))
        return 1
    cmd, args = args[0], args[1:]

    if cmd == "alembic":
        _alembic(args)


if __name__ == "__main__":
    sys.exit(main())


class DatabaseSchemaMismatch(Exception):
    """Exception raised when the database schema version does not match

    the current version of NbExchange.
    """


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


def register_foreign_keys(engine):
    """register PRAGMA foreign_keys=on on connection"""

    @event.listens_for(engine, "connect")
    def connect(dbapi_con, con_record):
        cursor = dbapi_con.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


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
            log.info(f"Stamping empty database with alembic revision {head}")
            alembic.command.stamp(cfg, head)
            return

        if "alembic_version" not in current_table_names:
            if "action" in current_table_names:
                rev = head
            else:
                rev = base
            log.debug("Stamping database schema version %s", rev)
            alembic.command.stamp(cfg, rev)

    # check database schema version
    # it should always be defined at this point
    alembic_revision = engine.execute(
        "SELECT version_num FROM alembic_version"
    ).first()[0]
    if alembic_revision == head:
        log.debug(f"database schema version found: {alembic_revision}")
        pass
    else:
        raise DatabaseSchemaMismatch(
            f"Found database schema version {alembic_revision} != {head}. "
            "Backup your database and run `nbexchange --upgrade-db`"
            " to upgrade to the latest schema."
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


def setup_db(url="sqlite:///:memory:", reset=False, log=None, **kwargs):
    """Check database revision and create all models"""

    log.info(f"dbutil.setup_db: db_url:{url}, reset:{reset}")
    if url.startswith("sqlite"):
        kwargs.setdefault("connect_args", {"check_same_thread": False})

    elif url.startswith("mysql"):
        kwargs.setdefault("pool_recycle", 60)

    if url.endswith(":memory:"):
        # If we're using an in-memory database, ensure that only one connection
        # is ever created.
        kwargs.setdefault("poolclass", StaticPool)

    engine = create_engine(url, **kwargs)

    if url.startswith("sqlite"):
        register_foreign_keys(engine)

    # enable pessimistic disconnect handling
    register_ping_connection(engine)

    if reset:
        Base.metadata.drop_all(engine)

    if mysql_large_prefix_check(engine):  # if mysql is allows large indexes
        add_row_format(Base)  # set format on the tables
    # check the db revision (will raise, pointing to `upgrade-db` if version doesn't match)
    check_db_revision(engine, log)

    Base.metadata.create_all(engine)
