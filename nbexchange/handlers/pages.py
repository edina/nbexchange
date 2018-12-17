import os
from nbexchange.base import BaseHandler


class EnvHandler(BaseHandler):
    urls = ["/env"]

    def get(self):
        self.finish(self.render_template("env.html", env=os.environ))


class HomeHandler(BaseHandler):
    urls = ["/"]

    def get(self):
        self.log.info(f"################  Hello World, this is home")
        self.write(f"################  Hello World, this is home")
