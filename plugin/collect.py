import io
import json
import os
import re
import shutil
import tarfile

import nbgrader.exchange.abc as abc
from .exchange import Exchange
from urllib.parse import quote_plus


class ExchangeCollect(abc.ExchangeCollect, Exchange):
    def init_src(self):
        pass

    def init_dest(self):
        pass

    def download(self, submission, dest_path):
        self.log.debug(f"ExchangeCollect.download - record {submission} to {dest_path}")
        r = self.api_request(
            f"collection?course_id={quote_plus(self.course_id)}&assignment_id={quote_plus(self.coursedir.assignment_id)}&path={quote_plus(submission['path'])}"
        )
        self.log.debug(
            f"Got back {r.status_code}  {r.headers['content-type']} after file download"
        )
        tgz = r.content

        try:
            tar_file = io.BytesIO(tgz)
            with tarfile.open(fileobj=tar_file) as handle:
                handle.extractall(path=dest_path)
        except Exception as e:  # TODO: exception handling
            self.fail(e.message)

    def do_collect(self):
        """Downloads multiple submitted files"""
        r = self.api_request(
            f"collections?course_id={quote_plus(self.course_id)}&assignment_id={quote_plus(self.coursedir.assignment_id)}"
        )

        self.log.debug(f"Got back {r} when listing collectable assignments")

        try:
            data = r.json()
        except json.decoder.JSONDecodeError:
            self.log.error(f"Got back an invalid response when listing assignments")
            return []

        if not data["success"]:
            self.fail("Error looking for assignments to collect")

        submissions = data["value"]

        self.log.debug(
            f"ExchangeCollect.do_collection found the following items: {submissions}"
        )

        if len(submissions) == 0:
            self.log.warning(
                f"No submissions of '{self.coursedir.assignment_id}' for course '{self.course_id}' to collect"
            )
        else:
            self.log.debug(
                f"Processing {len(submissions)} submissions of '{self.coursedir.assignment_id}' for course '{self.course_id}'"
            )

        for submission in submissions:

            # Work out the user-name from the path: '/some/path/submitted/course_2/tree 1/1_kiz/1544109991/fdc8c4ae-b3e0-4db6-859d-17852d65ec08.gz'
            regex = (
                f"/submitted/"
                + re.escape(self.course_id)
                + "/"
                + re.escape(self.coursedir.assignment_id)
                + "/([^/]+)/"
            )
            m = re.search(regex, submission["path"])
            if m:
                student_id = m.group(1)  # m.group(0) is the whole regex match

                if student_id:
                    local_dest_path = self.coursedir.format_path(
                        self.coursedir.submitted_directory,
                        student_id,
                        self.coursedir.assignment_id,
                    )
                    if not os.path.exists(os.path.dirname(local_dest_path)):
                        os.makedirs(os.path.dirname(local_dest_path))

                    self.log.debug(
                        f"ExchangeCollect.do_collection - collection dest : {local_dest_path}"
                    )

                    take_a_copy = False
                    updated_version = False
                    if os.path.isdir(local_dest_path):
                        existing_timestamp = self.coursedir.get_existing_timestamp(
                            local_dest_path
                        )
                        existing_timestamp = (
                            existing_timestamp.strftime(self.timestamp_format)
                            if existing_timestamp
                            else None
                        )
                        new_timestamp = submission["timestamp"]
                        if self.update and (
                            existing_timestamp is None
                            or new_timestamp > existing_timestamp
                        ):
                            take_a_copy = True
                            updated_version = True
                    else:
                        take_a_copy = True

                    if take_a_copy:
                        if updated_version:
                            self.log.info(
                                f"Updating submission: {student_id} {self.coursedir.assignment_id}"
                            )
                            # clear existing
                            shutil.rmtree(local_dest_path)
                        else:
                            self.log.info(
                                f"Collecting submission: {student_id} {self.coursedir.assignment_id}"
                            )
                        self.download(submission, local_dest_path)
                    else:
                        if self.update:
                            self.log.info(
                                f"No newer submission to collect: {student_id} {self.coursedir.assignment_id}"
                            )
                        else:
                            self.log.info(
                                f"Submission already exists, use --update to update: {student_id} {self.coursedir.assignment_id}"
                            )

    def copy_files(self):
        self.do_collect()
