import glob
import io
import json

import os

from .exchange import Exchange
from urllib.parse import quote_plus
import nbgrader.exchange.auth as auth


class ExchangeReleaseFeedback(auth.ExchangeReleaseFeedback, Exchange):

    src_path = None
    notebooks = None

    # where the downloaded files are placed
    def init_src(self):
        pass

    # where in the user tree
    def init_dest(self):
        pass

    def download(self):
        pass

    def copy_if_missing(self, src, dest, ignore=None):
        pass

    def do_copy(self, src, dest):
        pass

    def copy_files(self):
        pass
