import glob
import io
import json
import nbgrader.exchange.abc as abc
import os
import tempfile

from urllib.parse import quote_plus

from .exchange import Exchange


class ExchangeReleaseFeedback(abc.ExchangeReleaseFeedback, Exchange):

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
        the_file = tempfile.TemporaryFile()
        self.upload(tempfile)

    def upload(self, file):
        files = {"feedback" ("feedback.html", file)}

        url = f"feedback?course_id={quote_plus(self.course_id)}&assignment_id={quote_plus(self.coursedir.assignment_id)}"

        r = self.api_request(
            url,
            method="POST",
            files=files,
        )

        self.log.debug(f"Got back {r.status_code} after feedback upload")

        try:
            data = r.json()
        except json.decoder.JSONDecodeError:
            self.fail(r.text)

        if not data["success"]:
            self.fail(data["note"])

        self.log.info("Successfully uploaded feedback for assignment.")
