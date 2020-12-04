import os
from nbexchange.handlers.base import BaseHandler
from nbexchange.__version__ import __version__


class HomeHandler(BaseHandler):
    urls = ["/"]

    def get(self):
        self.finish(f"NbExchange {__version__}")
