from nbexchange.__version__ import __version__
from nbexchange.handlers.base import BaseHandler


class HomeHandler(BaseHandler):
    urls = ["/"]

    def get(self):
        self.finish(f"NbExchange {__version__}")
