import logging
import os
import sys
from datetime import datetime
from getpass import getuser

import sentry_sdk
from jupyterhub.log import CoroutineLogFormatter, log_request
from jupyterhub.utils import url_path_join
from sentry_sdk.integrations.tornado import TornadoIntegration
from sqlalchemy.exc import OperationalError
from tornado import web
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.log import access_log, app_log, gen_log
from tornado_prometheus import MetricsHandler, PrometheusMixIn
from traitlets import Bool, Dict, Integer, Type, Unicode, default
from traitlets.config import Application, catch_config_error

import nbexchange.dbutil
from nbexchange import dbutil, handlers
from nbexchange.handlers import base
from nbexchange.handlers.auth.naas_user_handler import NaasUserHandler
from nbexchange.handlers.auth.user_handler import BaseUserHandler

ROOT = os.path.dirname(__file__)
STATIC_FILES_DIR = os.path.join(ROOT, "static")


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

    config_file = Unicode("nbexchange_config.py", help="The config file to load").tag(config=True)

    base_url = os.environ.get("JUPYTERHUB_SERVICE_PREFIX", "/services/nbexchange/")
    base_storage_location = os.environ.get("NBEX_BASE_STORE", "/tmp/courses")
    # naas_url = os.environ.get("NAAS_URL", "https://127.0.0.1:8080")
    user_plugin_class = Type(
        NaasUserHandler,
        klass=BaseUserHandler,
        help="The class to use for handling users",
    ).tag(config=True)

    debug = bool(int(os.environ.get("DEBUG", 0)))

    ip = Unicode("0.0.0.0").tag(config=True)

    port = Integer(9000).tag(config=True)

    sentry_dsn = os.environ.get("SENTRY_DSN", "")

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
        return "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs).03d %(name)s %(module)s:%(lineno)d]%(end_color)s %(message)s"  # noqa: E501

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
    debug_db = Bool(False, help="log all database transactions. This has A LOT of output").tag(config=True)

    max_buffer_size = Integer(5253530000, help="The maximum size, in bytes, of an upload (defaults to 5GB)").tag(
        config=True
    )

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
                self.handlers.append((url_path_join(self.base_url, url), handler))

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

        # *NOT* adding 'max_buffer_size=self.max_buffer_size' here, as we handle the
        # size-checks in code (both plugin & exchange side)
        self.http_server = HTTPServer(self.tornado_application, xheaders=True)
        self.http_server.listen(self.port, address=self.ip)
        if run_loop:
            IOLoop.current().start()


if __name__ == "__main__":
    NbExchange.launch_instance()
