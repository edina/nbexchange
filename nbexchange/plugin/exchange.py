import fnmatch
import glob
import os
from datetime import datetime
from functools import partial
from textwrap import dedent
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import nbgrader.exchange.abc as abc
import requests
from nbgrader.auth import Authenticator
from nbgrader.exchange import ExchangeError
from traitlets import Bool, Integer, List, Unicode


class MockAuthenticator(Authenticator):
    super(Authenticator)

    def api_request(self, path, method="GET", *args, **kwargs):
        pass


class Exchange(abc.Exchange):

    path_includes_course = Bool(
        False,
        help=dedent(
            """
            Whether the path for fetching/submitting  assignments should be
            prefixed with the course name. If this is `False`, then the path
            will be something like `./ps1`. If this is `True`, then the path
            will be something like `./course123/ps1`.
            """
        ),
    ).tag(config=True)

    assignment_dir = Unicode(
        ".",
        help=dedent(
            """
            Local path for storing student assignments.  Defaults to '.'
            which is normally Jupyter's notebook_dir.
            """
        ),
    ).tag(config=True)

    base_service_url = Unicode(os.environ.get("NAAS_BASE_URL", "https://noteable.edina.ac.uk")).tag(config=True)

    def service_url(self):
        this_url = urljoin(self.base_service_url, "/services/nbexchange/")
        self.log.debug(f"service_url: {this_url}")
        return this_url

    course_id = Unicode(os.environ.get("NAAS_COURSE_ID", "no_course")).tag(config=True)

    max_buffer_size = Integer(5253530000, help="The maximum size, in bytes, of an upload (defaults to 5GB)").tag(
        config=True
    )

    ignore = List(
        [
            ".ipynb_checkpoints",
            "*.pyc",
            "__pycache__",
            "feedback",
        ],
        help=dedent(
            """
            List of file names or file globs.
            Upon submit, matching files and directories will be ignored.
            """
        ),
    ).tag(config=True)

    api_timeout = Integer(
        10,
        help="Timeout for plugin enquiries to the Exchange in seconds. Defaults to 10 seconds",
        config=True,
    )

    def check_timezone(self, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            value = value.replace(tzinfo=ZoneInfo(self.timezone))
        return value

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
            get_req = partial(requests.get, url, headers=headers, cookies=cookies, timeout=self.api_timeout)
            return get_req(*args, **kwargs)
        elif method == "POST":
            post_req = partial(requests.post, url, headers=headers, cookies=cookies, timeout=self.api_timeout)
            return post_req(*args, **kwargs)
        elif method == "DELETE":
            delete_req = partial(requests.delete, url, headers=headers, cookies=cookies, timeout=self.api_timeout)
            return delete_req(*args, **kwargs)
        else:
            raise NotImplementedError(f"HTTP Method {method} is not implemented")

    # Function from ELM
    def add_to_tar(self, tar_file, dir_path, exclude_patterns=[]):
        """
        Adds files to the tar file recursively from the directory path while excluding
        certain patterns.

        :param tar_file: TarFile object to add files to.
        :param dir_path: The directory path to start recursive addition.
        :param exclude_patterns: List of patterns to exclude.
        """
        for root, dirs, files in os.walk(dir_path):

            # skip any directories listed in exclude_patterns
            dirs[:] = [item for item in dirs if item not in exclude_patterns]

            for file in files:
                file_path = os.path.join(root, file)

                # Check if the file matches any of the exclude patterns
                if any(fnmatch.fnmatch(file, pattern) for pattern in exclude_patterns):
                    continue  # Skip this file if it matches a pattern

                # Calculate the arcname manually to preserve desired directory structure
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=dir_path)
                tar_file.add(file_path, arcname=arcname)

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
        self.set_timestamp()  # a datetime object
        if self.coursedir and not self.coursedir.course_id:
            self.coursedir.course_id = self.course_id

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
