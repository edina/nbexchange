import os
from nbexchange.handlers.base import BaseHandler
from nbexchange.__version__ import __version__


class EnvHandler(BaseHandler):
    urls = ["/env"]

    def get(self):
        self.finish(f"NB Exchange environment: {os.environ}")


class HomeHandler(BaseHandler):
    urls = ["/"]

    def get(self):
        self.log.info(f"NbExchange {__version__}")
        self.finish(f"NbExchange {__version__}")
