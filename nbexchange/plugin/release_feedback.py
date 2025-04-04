import glob
import json
import os
import re
from urllib.parse import quote_plus

import nbgrader.exchange.abc as abc
import requests
from dateutil import parser
from nbgrader.utils import make_unique_key, notebook_hash

from .exchange import Exchange


class ExchangeReleaseFeedback(abc.ExchangeReleaseFeedback, Exchange):
    src_path = None

    # where the downloaded files are placed
    def init_src(self):
        student_id = self.coursedir.student_id if self.coursedir.student_id else "*"
        self.src_path = self.coursedir.format_path(
            self.coursedir.feedback_directory, student_id, self.coursedir.assignment_id
        )

    # where in the user tree
    def init_dest(self):
        if self.coursedir.course_id == "":
            self.fail("No course id specified. Re-run with --course flag.")

    def copy_if_missing(self, src, dest, ignore=None):
        pass

    def do_copy(self, src, dest):
        pass

    def copy_files(self):
        if self.coursedir.student_id_exclude:
            exclude_students = set(self.coursedir.student_id_exclude.split(","))
        else:
            exclude_students = set()

        html_files = glob.glob(os.path.join(self.src_path, "*.html"))
        for html_file in html_files:
            regexp = re.escape(os.path.sep).join(
                [
                    os.path.normpath(
                        self.coursedir.format_path(
                            self.coursedir.feedback_directory,
                            "(?P<student_id>.*)",
                            self.coursedir.assignment_id,
                            escape=True,
                        )
                    ),
                    "(?P<notebook_id>.*).html",
                ]
            )

            m = re.match(regexp, html_file)
            if m is None:
                msg = "Could not match '%s' with regexp '%s'" % (html_file, regexp)
                self.log.error(msg)
                continue

            gd = m.groupdict()
            student_id = gd["student_id"]
            notebook_id = gd["notebook_id"]
            if student_id in exclude_students:
                self.log.debug("Skipping student '{}'".format(student_id))
                continue

            feedback_dir = os.path.split(html_file)[0]
            submission_dir = self.coursedir.format_path(
                self.coursedir.submitted_directory,
                student_id,
                self.coursedir.assignment_id,
            )

            try:
                timestamp = open(os.path.join(feedback_dir, "timestamp.txt")).read()
            except Exception:
                self.fail(f"timestamp file missing from {feedback_dir}")
            timestamp = self.check_timezone(parser.parse(timestamp)).strftime(self.timestamp_format)

            nbfile = os.path.join(submission_dir, "{}.ipynb".format(notebook_id))
            if not os.path.isfile(nbfile):
                self.fail(f"unable to find {nbfile} in submission files")
            unique_key = make_unique_key(
                self.coursedir.course_id,
                self.coursedir.assignment_id,
                notebook_id,
                student_id,
                timestamp,
            )

            self.log.debug("Unique key is: {}".format(unique_key))
            checksum = notebook_hash(nbfile, unique_key)

            self.log.info(
                "Releasing feedback for student '{}' on assignment '{}/{}/{}' ({})".format(
                    student_id,
                    self.coursedir.course_id,
                    self.coursedir.assignment_id,
                    notebook_id,
                    timestamp,
                )
            )

            self.upload(
                html_file,
                self.coursedir.assignment_id,
                student_id,
                notebook_id,
                timestamp,
                checksum,
            )

    def upload(self, html_file, assignment_id, student, notebook, timestamp, checksum):
        with open(html_file) as feedback_file:
            files = {"feedback": ("feedback.html", feedback_file.read())}

        url = (
            f"feedback?course_id={quote_plus(self.coursedir.course_id)}"
            f"&assignment_id={quote_plus(assignment_id)}"
            f"&notebook={quote_plus(notebook)}"
            f"&student={quote_plus(student)}"
            f"&timestamp={quote_plus(timestamp)}"
            f"&checksum={quote_plus(checksum)}"
        )

        try:
            r = self.api_request(url, method="POST", files=files)
        except requests.exceptions.Timeout:
            self.fail("Timed out trying to reach the exchange service to release feedback.")

        self.log.debug(f"Got back {r.status_code} after feedback upload")

        try:
            data = r.json()
        except json.decoder.JSONDecodeError as err:
            self.log.error("release_feedback failed upload\n" f"response text: {r.text}\n" f"JSONDecodeError: {err}")
            self.fail(r.text)

        if not data["success"]:
            self.fail(data["note"])

        self.log.info("Successfully uploaded feedback for assignment.")
