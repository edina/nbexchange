import logging
import os
import psycopg2
import sys

from datetime import datetime
from getpass import getuser
from jupyterhub.log import CoroutineLogFormatter, log_request

# from jupyterhub.services.auth import HubAuth
from jupyterhub.utils import url_path_join
from nbexchange import orm, dbutil, base, handlers
from nbexchange.handlers import assignment, submission
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from traitlets.config import Application, catch_config_error
from traitlets import (
    Bool,
    Dict,
    Integer,
    List,
    Unicode,
    default,
    TraitType,
    TraitError,
    class_of,
)
from tornado import web
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.log import app_log, access_log, gen_log
from raven.contrib.tornado import AsyncSentryClient

ROOT = os.path.dirname(__file__)
STATIC_FILES_DIR = os.path.join(ROOT, "static")


class UnicodeFromEnv(Unicode):
    """A Unicode trait that gets its default value from the environment
    Use .tag(env='VARNAME') to specify the environment variable to use.
    """

    def default(self, obj=None):
        sys.stderr.write(f"stderr - object: {obj}")
        env_key = self.metadata.get("env")
        sys.stderr.write(f"stderr - looking for: {env_key} in {os.environ}")
        if env_key in os.environ:
            return os.environ[env_key]
        else:
            return self.default_value


flags = {
    "debug": (
        {"Application": {"log_level": logging.DEBUG}},
        "set log level to logging.DEBUG (maximize logging output)",
    ),
    "upgrade-db": (
        {"NbExchange": {"upgrade_db": True}},
        """Automatically upgrade the database if needed on startup.

        Only safe if the database has been backed up.
        Only SQLite database files will be backed up automatically.
        """,
    ),
}


class NbExchange(Application):
    """The nbexchange application"""

    name = "nbexchange"

    @property
    def version(self):
        import pkg_resources

        return pkg_resources.get_distribution("nbexchange").version

    description = """
        Manage notebook submissions and collections for nbgrader
    """

    flags = Dict(flags)

    config_file = Unicode("nbexchange_config.py", help="The config file to load").tag(
        config=True
    )

    base_url = os.environ.get("JUPYTERHUB_SERVICE_PREFIX", "/services/nbexchange/")
    base_storage_location = os.environ.get("NBEX_BASE_STORE", "/tmp/courses")
    hub_api_url = os.environ.get("JUPYTERHUB_API_URL", "http://127.0.0.1:8081/hub/api/")
    hub_api_token = os.environ.get("JUPYTERHUB_API_TOKEN", "")
    hub_base_url = os.environ.get("JUPYTERHUB_BASE_URL", "http://127.0.0.1:8000/")
    naas_url = os.environ.get("NAAS_URL", "https://127.0.0.1:8080")
    debug = bool(int(os.environ.get("DEBUG", 0)))

    ip = Unicode("0.0.0.0").tag(config=True)

    port = Integer(9000).tag(config=True)

    sentry_dsn = UnicodeFromEnv("").tag(env="SENTRY_DSN", config=False)

    tornado_settings = Dict()

    _log_formatter_cls = CoroutineLogFormatter

    @default("log_level")
    def _log_level_default(self):
        if self.debug:
            return logging.DEBUG
        return logging.INFO

    @default("log_datefmt")
    def _log_datefmt_default(self):
        """Exclude date from default date format"""
        return "%Y-%m-%d %H:%M:%S"

    @default("log_format")
    def _log_format_default(self):
        """override default log format to include time"""
        return "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s %(module)s:%(lineno)d]%(end_color)s %(message)s"

    @staticmethod
    def add_url_prefix(prefix, handlers):
        """add a url prefix to handlers"""
        for i, tup in enumerate(handlers):
            lis = list(tup)
            lis[0] = url_path_join(prefix, tup[0])
            handlers[i] = tuple(lis)

        return handlers

    def init_logging(self):
        """Initialize logging"""
        # This prevents double log messages because tornado use a root logger that
        # self.log is a child of. The logging module dipatches log messages to a log
        # and all of its ancenstors until propagate is set to False.
        self.log.propagate = False

        _formatter = self._log_formatter_cls(
            fmt=self.log_format, datefmt=self.log_datefmt
        )

        # hook up tornado 3's loggers to our app handlers
        for log in (app_log, access_log, gen_log):
            # ensure all log statements identify the application they come from
            log.name = self.log.name
        logger = logging.getLogger("tornado")
        logger.propagate = True
        logger.parent = self.log
        logger.setLevel(self.log.level)

    db_url = os.environ.get("NBEX_DB_URL", "sqlite:///:memory:")  # nbexchange2.sqlite")

    db_kwargs = Dict(
        help="""Include any kwargs to pass to the database connection.
        See sqlalchemy.create_engine for details.
        """
    ).tag(config=True)
    upgrade_db = Bool(
        False,
        help="""Upgrade the database automatically on start.

        Only safe if database is regularly backed up.
        Only SQLite databases will be backed up to a local file automatically.
    """,
    ).tag(config=True)
    reset_db = Bool(False, help="Purge and reset the database.").tag(config=True)
    debug_db = Bool(
        False, help="log all database transactions. This has A LOT of output"
    ).tag(config=True)

    def _check_db_path(self, path):
        """More informative log messages for failed filesystem access"""
        path = os.path.abspath(path)
        parent, fname = os.path.split(path)
        user = getuser()
        if not os.path.isdir(parent):
            self.log.error(f"Directory {parent} does not exist")
        if os.path.exists(parent) and not os.access(parent, os.W_OK):
            self.log.error(f"{user} cannot create files in {parent}")
        if os.path.exists(path) and not os.access(path, os.W_OK):
            self.log.error(f"{user} cannot edit {path}")

    def init_db(self):
        """Initialize the nbexchange database"""
        self.log.debug(f"db_url = {self.db_url}")
        if self.upgrade_db:
            dbutil.upgrade_if_needed(self.db_url, log=self.log)

        try:
            self.session_factory = orm.new_session_factory(
                self.db_url,
                reset=self.reset_db,
                echo=self.debug_db,
                log=self.log,
                expire_on_commit=True,
                **self.db_kwargs,
            )
            self.db = self.session_factory()
        except OperationalError as e:
            self.log.error(f"Failed to connect to db: {self.db_url}")
            self.log.debug(f"Database error was:", exc_info=True)
            if self.db_url.startswith("sqlite:///"):
                self._check_db_path(self.db_url.split(":///", 1)[1])
            self.log.critical(
                "\n".join(
                    [
                        "If you recently upgraded NbExchange, try running",
                        "    nbexchange upgrade-db",
                        "to upgrade your nbexchange database schema",
                    ]
                )
            )
            self.exit(1)
        except orm.DatabaseSchemaMismatch as e:
            self.exit(e)

    def init_tornado_settings(self):
        """Initialize tornado config"""

        # if running from git directory, disable caching of require.js
        # otherwise cache based on server start time
        parent = os.path.dirname(ROOT)
        if os.path.isdir(os.path.join(parent, ".git")):
            version_hash = ""
        else:
            version_hash = (datetime.now().strftime("%Y%m%d%H%M%S"),)

        settings = dict(
            log_function=log_request,
            config=self.config,
            log=self.log,
            base_url=self.base_url,
            base_storage_location=self.base_storage_location,
            naas_url=self.naas_url,
            hub_base_url=self.hub_base_url,
            hub_api_url=self.hub_api_url,
            hub_api_token=self.hub_api_token,
            static_path=STATIC_FILES_DIR,
            static_url_prefix=url_path_join(self.base_url, "static/"),
            version_hash=version_hash,
            xsrf_cookies=False,
            debug=self.debug,
            # Replace the default [jupyterhub] database connection with our own **for our tornado app only**
            db=self.db,
        )
        # allow configured settings to have priority
        settings.update(self.tornado_settings)
        self.log.info(os.environ.get("JUPYTERHUB_API_URL"))
        self.log.info(settings)
        self.tornado_settings = settings

    def init_handlers(self):
        """Load nbexchange's tornado request handlers"""
        self.handlers = []

        for handler in handlers.default_handlers:
            for url in handler.urls:
                self.handlers.append((url_path_join(self.base_url, url), handler))

        self.handlers.append((r".*", base.Template404))
        self.log.info("##### ALL HANDLERS" + str(self.handlers))

    def init_tornado_application(self):
        self.tornado_application = web.Application(
            self.handlers, **self.tornado_settings
        )
        self.tornado_application.sentry_client = AsyncSentryClient(self.sentry_dsn)

    @catch_config_error
    def initialize(self, *args, **kwargs):
        """Load configuration settings."""
        super().initialize(*args, **kwargs)
        self.load_config_file(self.config_file)
        if self.subapp:
            return
        self.init_db()
        # self.init_hub_auth()
        self.init_tornado_settings()
        self.init_handlers()
        self.init_tornado_application()

    def stop(self):
        self.http_server.stop()

    def start(self, run_loop=True):
        if self.subapp:
            self.subapp.start()
            return

        self.http_server = HTTPServer(self.tornado_application, xheaders=True)
        self.http_server.listen(self.port, address=self.ip)
        if run_loop:
            IOLoop.current().start()


if __name__ == "__main__":
    NbExchange.launch_instance()
