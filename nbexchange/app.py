import logging
import os
import sys
from datetime import datetime
from getpass import getuser

import sentry_sdk
from jupyter_server.log import log_request
from jupyter_server.utils import url_path_join as ujoin
from sentry_sdk.integrations.tornado import TornadoIntegration
from sqlalchemy.exc import OperationalError
from tornado import web
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.log import LogFormatter, access_log, app_log, gen_log
from tornado_prometheus import MetricsHandler, PrometheusMixIn
from traitlets import Bool, Dict, Integer, Type, Unicode, default
from traitlets.config import Application, catch_config_error

import nbexchange.dbutil
from nbexchange import dbutil, handlers
from nbexchange.handlers import base
from nbexchange.handlers.auth.user_handler import BaseUserHandler

ROOT = os.path.dirname(__file__)
STATIC_FILES_DIR = os.path.join(ROOT, "static")


class MockUserHandler(BaseUserHandler):

    def get_current_user(self, request):
        return


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


class NbExchange(PrometheusMixIn, Application):
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

    config_file = Unicode("/etc/config/nbexchange_config.py", help="The config file to load", config=True)

    base_url = Unicode(
        "/services/nbexchange/",
        config=True,
        help="""
Base url for api queries into the exchange.
Defaults to '/services/nbexchange/'
""",
    )

    base_storage_location = Unicode(
        "/tmp/courses",
        config=True,
        help="""
Where the exchange stores the files uploaded.
Defaults to '/tmp/courses'
""",
    )

    db_url = Unicode(
        "sqlite:///:memory:",
        config=True,
        help="""
Where the exchange stores the files uploaded.
Defaults to 'sqlite:///:memory:' (an in-memory SQLite database)
""",
    )

    db_kwargs = Dict(
        config=True,
        help="""Include any kwargs to pass to the database connection.
        See sqlalchemy.create_engine for details.
        """,
    )

    upgrade_db = Bool(
        False,
        config=True,
        help="""Upgrade the database automatically on start.

        Only safe if database is regularly backed up.
        Only SQLite databases will be backed up to a local file automatically.
    """,
    )

    reset_db = Bool(False, config=True, help="Purge and reset the database.")
    debug_db = Bool(False, config=True, help="log all database transactions. This has A LOT of output")

    max_buffer_size = Integer(
        5253530000, config=True, help="The maximum size, in bytes, of an upload (defaults to 5GB)"
    )

    user_plugin_class = Type(
        MockUserHandler,
        # NaasUserHandler,
        klass=BaseUserHandler,
        config=True,
        help="The class to use for handling users",
    )

    debug = Bool(False, config=True, help="Sets logging level to DEBUG, defaults to 0/False")

    ip = Unicode("0.0.0.0", config=True)

    port = Integer(9000, config=True)

    sentry_dsn = os.environ.get("SENTRY_DSN", "")

    tornado_settings = Dict()

    _log_formatter_cls = LogFormatter

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
        return "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s %(module)s:%(lineno)d]%(end_color)s %(message)s"  # noqa: E501

    @staticmethod
    def add_url_prefix(prefix, handlers):
        """add a url prefix to handlers"""
        for i, tup in enumerate(handlers):
            lis = list(tup)
            lis[0] = ujoin(prefix, tup[0])
            handlers[i] = tuple(lis)

        return handlers

    def init_logging(self):
        """Initialize logging"""
        # This prevents double log messages because tornado use a root logger that
        # self.log is a child of. The logging module dipatches log messages to a log
        # and all of its ancenstors until propagate is set to False.
        self.log.propagate = False

        # Is this actually used anywhere? flake says it isn't
        # _formatter = self._log_formatter_cls(fmt=self.log_format, datefmt=self.log_datefmt)

        # hook up tornado 3's loggers to our app handlers
        for log in (app_log, access_log, gen_log):
            # ensure all log statements identify the application they come from
            log.name = self.log.name
        logger = logging.getLogger("tornado")
        logger.propagate = True
        logger.parent = self.log
        logger.setLevel(self.log.level)

        access_log.propagate = False
        # make sure access log is enabled even if error level is WARNING|ERROR
        access_log.setLevel(logging.INFO)
        stdout_handler = logging.StreamHandler(sys.stdout)
        access_log.addHandler(stdout_handler)

    def _check_db_path(self, path):
        """More informative log messages for failed filesystem access"""
        path = os.path.abspath(path)
        parent, fname = os.path.split(path)
        user = getuser()  # this is the user running the notebook-server
        if not os.path.isdir(parent):
            self.log.error(f"Directory {parent} does not exist")
        if os.path.exists(parent) and not os.access(parent, os.W_OK):
            self.log.error(f"{user} cannot create files in {parent}")
        if os.path.exists(path) and not os.access(path, os.W_OK):
            self.log.error(f"{user} cannot edit {path}")

    def init_db(self):
        """Initialize the nbexchange database"""
        self.log.debug(f"app.py.init_db: db_url = {self.db_url}")
        # print(f"app.py.init_db: db_url = {self.db_url}")
        if self.upgrade_db:
            dbutil.upgrade_if_needed(self.db_url, log=self.log)

        try:
            nbexchange.dbutil.setup_db(
                self.db_url,
                reset=self.reset_db,
                echo=self.debug_db,
                log=self.log,
                **self.db_kwargs,
            )
        except OperationalError as e:
            self.log.error(f"Failed to connect to db: {self.db_url}")
            self.log.debug(f"Database error was: {e}", exc_info=True)
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
        except nbexchange.dbutil.DatabaseSchemaMismatch as e:
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
            # naas_url=self.naas_url,
            max_buffer_size=self.max_buffer_size,
            user_plugin=self.user_plugin_class(),
            version_hash=version_hash,
            xsrf_cookies=False,
            debug=self.debug,
        )
        # allow configured settings to have priority
        settings.update(self.tornado_settings)
        self.log.info(settings)
        self.tornado_settings = settings

    def init_handlers(self):
        """Load nbexchange's tornado request handlers"""
        self.handlers = []

        for handler in handlers.default_handlers:
            for url in handler.urls:
                self.handlers.append((ujoin(self.base_url, url), handler))

        self.handlers.append((r"/metrics", MetricsHandler))

        self.handlers.append((r".*", base.Template404))
        self.log.debug("##### ALL HANDLERS" + str(self.handlers))

    def init_tornado_application(self):
        self.tornado_application = web.Application(self.handlers, **self.tornado_settings)
        if self.sentry_dsn:
            sentry_sdk.init(
                dsn=self.sentry_dsn,
                integrations=[TornadoIntegration()],
                release="nbexchange@" + os.environ.get("COMMIT_SHA", "untagged"),
            )

    @catch_config_error
    def initialize(self, *args, **kwargs):
        """Load configuration settings."""
        logging.info("app.initialisze called")

        super().initialize(*args, **kwargs)
        logging.info("app.initialisze loading config file")
        self.load_config_file(self.config_file)
        if self.subapp:
            return
        logging.info(f"app.initialisze - db_url: {self.db_url}")
        self.init_db()
        logging.info("app.initialisze init_db completed")
        self.init_tornado_settings()
        logging.info("app.initialisze init_tornado_settings completed")
        self.init_handlers()
        logging.info("app.initialisze init_handlers completed")
        self.init_tornado_application()
        logging.info("app.initialisze init_tornado_application completed")

    def stop(self):
        self.http_server.stop()

    def start(self, run_loop=True):
        logging.info("app.start called")
        if self.subapp:
            self.subapp.start()
            return
        logging.info("app.start not a subapp")

        # *NOT* adding 'max_buffer_size=self.max_buffer_size' here, as we handle the
        # size-checks in code (both plugin & exchange side)
        self.http_server = HTTPServer(self.tornado_application, xheaders=True)
        self.http_server.listen(self.port, address=self.ip)
        logging.info("app.start about to hit the IOLoop start")
        if run_loop:
            IOLoop.current().start()


if __name__ == "__main__":
    NbExchange.launch_instance()
