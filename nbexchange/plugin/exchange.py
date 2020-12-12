import datetime
import glob
from collections import Sequence, defaultdict

import nbgrader.exchange.abc as abc
import os
import requests

from dateutil.tz import gettz
from functools import partial
from nbgrader.exchange import ExchangeError
from nbgrader.utils import full_split
from traitlets import Unicode, Bool, Instance
from urllib.parse import urljoin


class Exchange(abc.Exchange):

    # Temporary configuration to transition from 1.1 to 1.3
    use_1_2_behaviour = Bool(
        False,
        help="""
Defines which mode of code is used (defaults to false)
If this is False (or does not exist), everything uses the old paths &
methods (pre version 1.2.0).
If it's True, it allows 'check_for_old_formgrader_paths' &
'support_old_feedback' (version 1.2.x)
This flag (and it's sub flags) will disappear for version 1.3+
"""
    ).tag(config=True)

    use_course_path_everywhere = Bool(
        False,
        help="""
This switches the code to put *all* nbgrader _step_ folders inside
the course_code directory.
This is useful as it creates separate islands for each course.

This defaults to False, which means the plugin emulates the standard
nbgrader and puts all directorys in the current directory (or $HOME
in the web UI)

This flag is primarily used for Instructors. If you are configuring
students, then 'path_includes_course' is perfectly valid.
        """
    ).tag(config=True)

    check_for_old_formgrader_paths = Bool(
        False,
        help="""
To enable old bad coding to be corrected, some old behaviour needs to
be supported for a time.

eg: 'source' & 'release' started off not recognising the config option
'path_includes_course' - so there will be a period of time where existing
course-work needs to check whether things should be found (and
continue to be filed) using the old system or move to the new.

If this flag is 'true', then the code will check if
'$HOME/source/assignment_id' exists

* If it does the code will *not* honour the 'path_includes_course' config.
* If not, then the code *will* honour the 'path_includes_course' config.
        """,
    ).tag(config=True)

    support_old_feedback = Bool(
        True,
        help="""
Toggles between per file feedback (<1.2), and gzipped feedback (which is what
everything else does)

If True, it will check if the `assignment_list` return `feedback_xxx` keys for
notebook dicts

* If it does, we use the old per file and summerize system
* If not, we use the new ungzip into folder system
        """,
    ).tag(config=True)

    path_includes_course = Bool(
        False,
        help="""
Whether the path for fetching/submitting  assignments should be
prefixed with the course name. If this is `False`, then the path
will be something like `./ps1`. If this is `True`, then the path
will be something like `./course123/ps1`.

Note: this _only_ changes fetching/submitting  assignments, it
has no impact on the Formgrade paths.
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
