import os
from nbexchange.base import BaseHandler
from nbexchange.__version__ import __version__


class EnvHandler(BaseHandler):
    urls = ["/env"]

    def get(self):
        self.finish(self.render_template("env.html", env=os.environ))


class HomeHandler(BaseHandler):
    urls = ["/"]

    def get(self):
        self.log.info(f"NbExchange {__version__}")
        self.write(f"NbExchange {__version__}")
