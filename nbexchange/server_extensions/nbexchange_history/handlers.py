import contextlib
import json
import os
import traceback
from urllib.parse import urlparse

from jupyter_core.paths import jupyter_config_path
from nbgrader.apps import NbGrader
from nbgrader.auth import Authenticator
from nbgrader.exchange import ExchangeError
from notebook.base.handlers import IPythonHandler
from notebook.utils import url_path_join as ujoin
from tornado import web
from traitlets.config import LoggingConfigurable
from nbexchange.models.users import User

from ...plugin import ExchangeHistory

static = os.path.join(os.path.dirname(__file__), "static")


# @contextlib.contextmanager
# def chdir(dirname):
#     currdir = os.getcwd()
#     os.chdir(dirname)
#     yield
#     os.chdir(currdir)


class BaseHistorytHandler(IPythonHandler):
    @property
    def manager(self):
        self.log.info("SERVER - manager(self)")

        self.log.info(User)
        return self.settings["history_list_manager"]


class HistoryListHandler(BaseHistorytHandler):
    @web.authenticated
    def get(self):
        self.finish(json.dumps(self.manager.list_history()))


class HistoryList(LoggingConfigurable):
    @property
    def assignment_dir(self):
        self.log.info("SERVER - Assignment dir")
        return self.settings["assignment_dir"]

    def get_base_url(self):
        parts = urlparse(self.request.full_url())
        base_url = parts.scheme + "://" + parts.netloc
        return base_url.rstrip("/")

    def load_config(self):
        self.log.info("Load History")
        paths = jupyter_config_path()
        paths.insert(0, os.getcwd())

        app = NbGrader()
        app.config_file_paths.append(paths)
        app.load_config_file()

        return app.config

    @contextlib.contextmanager
    def get_history_config(self):
        self.log.info("SERVER - Get History Config")

        app = NbGrader()
        self.log.info("SERVER - Set app to nbgrader")
        self.log.info(app)
        app.config_file_paths.append(os.getcwd())
        self.log.info("SERVER - getcwd")
        self.log.info(app.config_file_paths)
        app.load_config_file()

        self.log.info("SERVER - Load Config file")

        yield app.config

    def list_history(self):

        self.log.info("SERVER - List History")
        retvalue = {"success": False, "value": "No history to list"}
        with self.get_history_config() as config:
            try:
                self.log.info("SERVER - authenticator")
                authenticator = Authenticator(config=config)
                self.log.info(authenticator)
                self.log.info("SERVER - config")
                lister = ExchangeHistory(authenticator=authenticator, config=config)
                self.log.info(config)
                self.log.info("SERVER - Start lister")
                self.log.info(lister)
                courses = lister.start()

            except Exception as e:
                self.log.error(traceback.format_exc())
                if isinstance(e, ExchangeError):
                    retvalue = {"success": False, "value": "NBExchange failed to find plugins."}
                else:
                    retvalue = {"success": False, "value": traceback.format_exc()}
            else:
                retvalue = {"success": True, "value": courses}
        return retvalue


default_handlers = [(r"/history", HistoryListHandler)]


def load_jupyter_server_extension(nbapp):
    """Load the nbserver"""
    nbapp.log.info("Loading the history_list nbexchange serverextension")
    webapp = nbapp.web_app
    webapp.settings["history_list_manager"] = HistoryList(parent=nbapp)
    base_url = webapp.settings["base_url"]
    webapp.add_handlers(".*$", [(ujoin(base_url, pat), handler) for pat, handler in default_handlers])
