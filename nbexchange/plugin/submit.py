import io
import json
import os
import sys
import tarfile
import time
from contextlib import closing
from urllib.parse import quote_plus

import requests
from dateutil import parser
from nbgrader.exchange.abc import ExchangeSubmit as ABCExchangeSubmit
from nbgrader.utils import find_all_notebooks

from .exchange import Exchange
from .list import ExchangeList


class ExchangeSubmit(Exchange, ABCExchangeSubmit):
    def do_copy(self, src, dest):
        pass

    def init_src(self):
        root = ""
        if self.path_includes_course:
            root = os.path.join(self.coursedir.course_id, self.coursedir.assignment_id)
        else:
            root = self.coursedir.assignment_id
        self.src_path = os.path.abspath(os.path.join(self.assignment_dir, root))
        if not os.path.isdir(self.src_path):
            self._assignment_not_found(self.src_path, root)
        self.log.debug(f"ExchangeSubmit.init_src ensuring {self.src_path} exists")

    def init_dest(self):
        if self.coursedir.course_id == "":
            self.fail("No course id specified. Re-run with --course flag.")

    # The submitted files have a timestamp.txt file with them.
    def tar_source(self):
        timestamp = self.timestamp  # This is a string object
        tar_file = io.BytesIO()
        with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
            self.add_to_tar(tar_handle, self.src_path, self.ignore)
            with closing(io.BytesIO(timestamp.encode())) as fobj:
                tarinfo = tarfile.TarInfo("timestamp.txt")
                tarinfo.size = len(fobj.getvalue())
                tarinfo.mtime = time.time()
                tar_handle.addfile(tarinfo, fileobj=fobj)
        tar_file.seek(0)
        return tar_file.read(), timestamp

    def upload(self, file: bytes, timestamp: str):
        self.log.debug(f"ExchangeSubmit uploading to: {self.service_url()}")
        self.log.info(f"Source: {self.src_path}")
        self.log.info("Destination: The exhange service")

        # validate timestamp
        timestamp = self.check_timezone(parser.parse(timestamp)).strftime(self.timestamp_format)

        files = {"assignment": ("assignment.tar.gz", file)}
        try:
            r = self.api_request(
                f"submission?course_id={quote_plus(self.coursedir.course_id)}&assignment_id={quote_plus(self.coursedir.assignment_id)}&timestamp={quote_plus(timestamp)}",  # noqa: E501
                method="POST",
                files=files,
            )
        except requests.exceptions.Timeout:
            self.fail("Timed out trying to reach the exchange service to post submission.")

        self.log.debug(f"Got back {r.status_code} after file upload")
        try:
            data = r.json()
        except json.decoder.JSONDecodeError as err:
            self.log.error("release_feedback failed upload\n" f"response text: {r.text}\n" f"JSONDecodeError: {err}")
            self.fail(r.text)
        if not data["success"]:
            self.fail(data["note"])

        self.log.info(f"Submitted as: {self.coursedir.course_id} {self.coursedir.assignment_id} {timestamp}")

    # Like the default Submit, we log differences, and do not render then in the display
    # (not sure that's any ues to anyone - but that's what the original does)
    def check_filename_diff(self):
        # List of filenames, no paths
        released_notebooks = []

        assignments = ExchangeList.query_exchange(self)
        latest_timestamp = "1990-01-01 00:00:00"
        for assignment in assignments:
            # We want the last released version of this assignments
            if self.coursedir.assignment_id == assignment["assignment_id"] and assignment.get("status") == "released":
                if assignment.get("timestamp") > latest_timestamp:
                    latest_timestamp = assignment.get("timestamp")
                    released_notebooks = [
                        n["notebook_id"] + ".ipynb" for n in assignment["notebooks"] if "notebook_id" in n
                    ]
                else:
                    continue

        submitted_notebooks = find_all_notebooks(self.src_path)

        # Now look for missing notebooks in submitted notebooks
        missing = False
        release_diff = list()
        for filename in released_notebooks:
            if filename in submitted_notebooks:
                release_diff.append("{}: {}".format(filename, "FOUND"))
            else:
                missing = True
                release_diff.append("{}: {}".format(filename, "MISSING"))

        # Look for extra notebooks in submitted notebooks
        extra = False
        submitted_diff = list()
        for filename in submitted_notebooks:
            if filename in released_notebooks:
                submitted_diff.append("{}: {}".format(filename, "OK"))
            else:
                extra = True
                submitted_diff.append("{}: {}".format(filename, "EXTRA"))

        if missing or extra:
            diff_msg = "Expected:\n\t{}\nSubmitted:\n\t{}".format(
                "\n\t".join(release_diff), "\n\t".join(submitted_diff)
            )
            if missing and self.strict:
                self.fail(
                    "Assignment {} not submitted. "
                    "There are missing notebooks for the submission:\n{}"
                    "".format(self.coursedir.assignment_id, diff_msg)
                )
            else:
                self.log.warning(
                    "Possible missing notebooks and/or extra notebooks "
                    "submitted for assignment {}:\n{}"
                    "".format(self.coursedir.assignment_id, diff_msg)
                )

    def copy_files(self):
        self.check_filename_diff()
        # Grab files from hard drive, and the timestamp string we put in the timestamp file
        file, timestamp = self.tar_source()
        if sys.getsizeof(file) > self.max_buffer_size:
            self.fail(
                f"Assignment {self.coursedir.assignment_id} not submitted. "
                "The contents of your assignment are too large:\n"
                "The total size of all files in your assignment directory [excluding any feedback], when compressed "
                f"using tar -czvf must be less than {self.max_buffer_size} bytes.\n"
                "You may have large data files, temporary files, and/or working files that should not be included"
                " - try deleting them."
            )
        # Upload files to exchange
        self.upload(file, timestamp)
