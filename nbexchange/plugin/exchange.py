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


def contains_format(string, formats):
    return any(f"{{{fmt}}}" in string for fmt in formats)


def maybe_format(string, **values):
    try:
        return string.format(**values)
    except KeyError:
        return string


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

    def set_timestamp(self):
        """Set the timestap using the configured timezone."""
        tz = gettz(self.timezone)
        if tz is None:
            self.fail("Invalid timezone: {}".format(self.timezone))
        self.timestamp = datetime.datetime.now(tz).strftime(self.timestamp_format)

    def api_request(self, path, method="GET", *args, **kwargs):

        jwt_token = os.environ.get("NAAS_JWT")

        cookies = dict()
        headers = dict()

        if jwt_token:
            cookies["noteable_auth"] = jwt_token

        url = self.service_url() + path

        self.log.info(f"Exchange.api_request calling exchange with url {url}")

        if method == "GET":
            get_req = partial(requests.get, url, headers=headers, cookies=cookies)
            self.log.info(f"Exchange.api_request GET returning {get_req}")
            return get_req(*args, **kwargs)
        elif method == "POST":
            post_req = partial(requests.post, url, headers=headers, cookies=cookies)
            return post_req(*args, **kwargs)
        elif method == "DELETE":
            delete_req = partial(requests.delete, url, headers=headers, cookies=cookies)
            return delete_req(*args, **kwargs)
        else:
            raise NotImplementedError(f"HTTP Method {method} is not implemented")

    def get_directory_structure(
        self, step, course_id=None, user_id=None, assignment_id=None
    ):
        structure = [self.coursedir.root]
        if self.path_includes_course:
            if course_id is None:
                self.log.info(
                    "Trying to get directory structure that includes course id without specifying course id"
                )
                return []
            structure.append(course_id)
        structure.extend(full_split(self.coursedir.directory_structure))
        full_structure = []
        fmtstrs = ["nbgrader_step", "student_id", "assignment_id"]
        fmt = {"nbgrader_step": step}
        if user_id is not None:
            fmt["student_id"] = user_id
        if assignment_id is not None:
            fmt["assignment_id"] = assignment_id

        for part in structure:
            the_part = maybe_format(part, **fmt)
            if (
                len(full_structure) > 0
                and not contains_format(the_part, fmtstrs)
                and not contains_format(full_structure[-1], fmtstrs)
            ):
                full_structure[-1] = os.path.join(full_structure[-1], the_part)
            else:
                full_structure.append(the_part)
        return full_structure

    def group_by(self, key, files):
        ordered = defaultdict(list)
        for item in files:
            if key in item.get("details", {}):
                ordered[item["details"][key]] = item
        return ordered

    def get_files(self, root, structure=None, **kwargs):
        print(f"> get files called {root} [ {structure} ]")

        fmtstrs = ["nbgrader_step", "student_id", "assignment_id"]
        if structure is None:
            structure = []

        if isinstance(root, list):
            return self.get_files(root[0], root[1:] + structure, **kwargs)

        if len(structure) == 0:
            if os.path.isdir(root):
                files = os.listdir(root)
                return [
                    {"files": [os.path.join(root, f) for f in files], "details": kwargs}
                ]
            else:
                return []

        if not contains_format(structure[0], fmtstrs):
            root = os.path.join(root, structure[0])
            return self.get_files(root, structure[1:], **kwargs)
        files = []
        if os.path.exists(root):
            for filename in os.listdir(root):
                new_root = os.path.join(root, filename)
                detail_name = structure[0].strip("{}")
                kwargs[detail_name] = filename
                if os.path.isdir(new_root):
                    files.extend(self.get_files(new_root, structure[1:], **kwargs))
        else:
            print(">> path doesn't exist, returning empty")
            return []
        print(f">> returning {files}")
        return files

    def get_local_assignments(self, assignments, user_id=None, course_id=None):
        print(f"> get local assignments called")
        print(f">.. assignments {assignments}")
        print(f">.. user_id {user_id}; course_id {course_id}")

        found_assignments = []
        for assign in assignments:
            found_assignments.extend(
                [
                    {
                        "details": {"assignment_id": assign, **x["details"]},
                        "files": x["files"],
                    }
                    for x in self.get_files(
                        self.get_directory_structure(
                            self.assignment_dir,
                            course_id=course_id,
                            user_id=user_id,
                            assignment_id=assign,
                        )
                    )
                ]
            )
        return found_assignments

    def get_local_submissions(self, user_id=None, course_id=None):
        return self.get_files(
            self.get_directory_structure(
                self.coursedir.submitted_directory, course_id=course_id, user_id=user_id
            )
        )

    def get_local_feedback(self, user_id=None, course_id=None, assignment_id=None):
        return self.get_files(
            self.get_directory_structure(
                self.coursedir.feedback_directory, course_id=course_id, user_id=user_id
            )
        )

    def save_local_assignments(self, user_id, course_id, assignment):
        pass

    def save_local_submission(self, user_id, course_id, submission):
        pass

    def save_local_feedback(self, user_id, course_id, assignment_id, feedback):
        pass

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
        self.log.info(f"Called start on {self.__class__.__name__}")

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
