import base64
import io
import json

import nbgrader.exchange.abc as abc
import os
import shutil
import tarfile
import tempfile

from nbgrader.api import new_uuid
from traitlets import Bool
from urllib.parse import quote_plus

from .exchange import Exchange


class ExchangeFetchFeedback(abc.ExchangeFetchFeedback, Exchange):

    # where the downloaded files are placed
    def init_src(self):
        self.src_path = ""
        # self.log.debug(
        #     f"ExchangeFetchFeedback.init_src using {self.course_id} {self.coursedir.assignment_id}"
        # )
        #
        # location = "/".join(
        #     [
        #         "/tmp/",
        #         new_uuid(),
        #         self.course_id,
        #         self.coursedir.assignment_id,
        #         self.coursedir.notebook_id,
        #         "feedback.html",
        #     ]
        # )
        # os.makedirs(os.path.dirname(location), exist_ok=True)
        # self.src_path = location
        # self.log.debug(f"ExchangeFetchFeedback.init_src ensuring {self.src_path}")

    # where in the user tree
    def init_dest(self):
        if self.path_includes_course:
            root = os.path.join(self.coursedir.course_id, self.coursedir.assignment_id)
        else:
            root = self.coursedir.assignment_id
        self.dest_path = os.path.abspath(os.path.join(self.assignment_dir, root, 'feedback'))
        os.makedirs(self.dest_path + "/", exist_ok=True)
        self.log.debug(f"ExchangeFetchFeedback.init_dest ensuring {self.dest_path}")

    def download(self):
        self.log.info(f"Download {quote_plus(self.coursedir.notebook_id)} from {self.service_url}")
        r = self.api_request(
            f"feedback?assignment_id={quote_plus(self.coursedir.assignment_id)}"
        )
        self.log.info(
            f"Got back {r.status_code} {r.headers['content-type']} after file download"
        )
        content = r.json()
        if "feedback" in content:
            for f in content["feedback"]:
                try:
                    with open(os.path.join(self.dest_path, f["filename"]), "wb") as handle:
                        handle.write(base64.b64decode(f["content"]))
                except Exception as e:  # TODO: exception handling
                    self.fail(str(e))
        else:
            self.fail(content.get("note", "could not get feedback"))

    def do_copy(self, src, dest):
        """Copy the src dir to the dest dir omitting the self.coursedir.ignore globs."""
        self.download()
        # shutil.copy(src, dest)
        # # clear tmp having downloaded file
        # os.remove(self.src_path)

    def copy_files(self):
        self.log.debug(f"Source: {self.src_path}")
        self.log.debug(f"Destination: {self.dest_path}")
        self.do_copy(self.src_path, self.dest_path)
        self.log.debug(f"Fetched as: {self.coursedir.notebook_id}")
