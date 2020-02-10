import io
import os
import shutil
import tarfile
import tempfile

from nbgrader.api import new_uuid
from .exchange import Exchange
from traitlets import Bool
from urllib.parse import quote_plus

import nbgrader.exchange.abc as abc


class ExchangeFetchFeedback(abc.ExchangeFetchAssignment, Exchange):

    path_includes_course = Bool(
        True, help="Whether assigments are 'fetched' into course-specific trees"
    ).tag(config=True)


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
