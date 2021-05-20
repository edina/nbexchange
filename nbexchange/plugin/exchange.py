import datetime
import glob
import os
from collections.abc import Sequence
from functools import partial
from urllib.parse import urljoin

import nbgrader.exchange.abc as abc
import requests
from dateutil.tz import gettz
from nbgrader.exchange import ExchangeError
from nbgrader.utils import full_split
from traitlets import Bool, Instance, Unicode


class Exchange(abc.Exchange):

    path_includes_course = Bool(
        False,
        help="""
Whether the path for fetching/submitting  assignments should be
prefixed with the course name. If this is `False`, then the path
will be something like `./ps1`. If this is `True`, then the path
will be something like `./course123/ps1`.
""",
    ).tag(config=True)

    assignment_dir = Unicode(
        ".",
        help="""
Local path for storing student assignments.  Defaults to '.'
which is normally Jupyter's notebook_dir.
""",
    ).tag(config=True)

    base_service_url = Unicode(
        os.environ.get("NAAS_BASE_URL", "https://noteable.edina.ac.uk")
    ).tag(config=True)

    def service_url(self):
        this_url = urljoin(self.base_service_url, "/services/nbexchange/")
        self.log.debug(f"service_url: {this_url}")
        return this_url

    course_id = Unicode(os.environ.get("NAAS_COURSE_ID", "no_course")).tag(config=True)

    def fail(self, msg):
        self.log.fatal(msg)
        raise ExchangeError(msg)

    def api_request(self, path, method="GET", *args, **kwargs):

        jwt_token = os.environ.get("NAAS_JWT")

        cookies = dict()
        headers = dict()

        if jwt_token:
            cookies["noteable_auth"] = jwt_token

        url = self.service_url() + path

        self.log.debug(f"Exchange.api_request calling exchange with url {url}")

        if method == "GET":
            get_req = partial(requests.get, url, headers=headers, cookies=cookies)
            return get_req(*args, **kwargs)
        elif method == "POST":
            post_req = partial(requests.post, url, headers=headers, cookies=cookies)
            return post_req(*args, **kwargs)
        elif method == "DELETE":
            delete_req = partial(requests.delete, url, headers=headers, cookies=cookies)
            return delete_req(*args, **kwargs)
        else:
            raise NotImplementedError(f"HTTP Method {method} is not implemented")

    def init_src(self):
        """Compute and check the source paths for the transfer."""
        raise NotImplementedError

    def init_dest(self):
        """Compute and check the destination paths for the transfer."""
        raise NotImplementedError

    def copy_files(self):
        """Actually do the file transfer."""
        raise NotImplementedError

    def do_copy(self, src, dest):
        """Copy the src dir to the dest dir omitting the self.coursedir.ignore globs."""
        raise NotImplementedError

    def start(self):
        self.log.debug(f"Called start on {self.__class__.__name__}")

        self.init_src()
        self.init_dest()
        self.copy_files()

    def _assignment_not_found(self, src_path, other_path):
        msg = f"Assignment not found at: {src_path}"
        self.log.fatal(msg)
        found = glob.glob(other_path)
        if found:
            # Normally it is a bad idea to put imports in the middle of
            # a function, but we do this here because otherwise fuzzywuzzy
            # prints an annoying message about python-Levenshtein every
            # time nbgrader is run.
            from fuzzywuzzy import fuzz

            scores = sorted([(fuzz.ratio(self.src_path, x), x) for x in found])
            self.log.error("Did you mean: %s", scores[-1][1])

        raise ExchangeError(msg)
