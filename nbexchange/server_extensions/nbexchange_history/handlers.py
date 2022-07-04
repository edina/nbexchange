import contextlib
import json
import os
import traceback
from textwrap import dedent
from urllib.parse import urlparse

from jupyter_core.paths import jupyter_config_path
from nbgrader import __version__ as nbgrader_version
from nbgrader.apps import NbGrader
from nbgrader.auth import Authenticator
from nbgrader.exchange import ExchangeError
from notebook.base.handlers import IPythonHandler
from notebook.utils import url_path_join as ujoin
from tornado import web
from traitlets import Unicode, default
from traitlets.config import Config, LoggingConfigurable

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
        return self.settings["history_list_manager"]


class HistoryListHandler(BaseHistorytHandler):
    @web.authenticated
    def get(self):
        self.finish(json.dumps(self.manager.list_history()))


class HistoryList(LoggingConfigurable):
    @property
    def assignment_dir(self):
        return self.settings["assignment_dir"]

    def get_base_url(self):
        parts = urlparse(self.request.full_url())
        base_url = parts.scheme + "://" + parts.netloc
        return base_url.rstrip("/")

    def load_config(self):
        paths = jupyter_config_path()
        paths.insert(0, os.getcwd())

        app = NbGrader()
        app.config_file_paths.append(paths)
        app.load_config_file()

        return app.config

    @contextlib.contextmanager
    def get_history_config(self):
        config = self.load_config()

        lister = ExchangeHistory(config=config)

        app = NbGrader()
        app.config_file_paths.append(os.getcwd())
        app.load_config_file()

        yield app.config

    def list_history(self):

        retvalue = {"success": False, "value": "No history to list"}
        with self.get_history_config() as config:
            try:
                authenticator = Authenticator(config=config)
                lister = ExchangeHistory(authenticator=authenticator, config=config)
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
