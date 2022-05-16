import base64
import os
from urllib.parse import quote_plus

import nbgrader.exchange.abc as abc

from .exchange import Exchange


class ExchangeFetchFeedback(abc.ExchangeFetchFeedback, Exchange):

    # where the downloaded files are placed
    def init_src(self):
        if self.coursedir.course_id == "":
            self.fail("No course id specified. Re-run with --course flag.")

    # where in the user tree
    def init_dest(self):
        if self.path_includes_course:
            root = os.path.join(self.coursedir.course_id, self.coursedir.assignment_id)
        else:
            root = self.coursedir.assignment_id
        self.dest_path = os.path.abspath(os.path.join(self.assignment_dir, root, "feedback"))
        os.makedirs(self.dest_path + "/", exist_ok=True)
        self.log.debug(f"ExchangeFetchFeedback.init_dest ensuring {self.dest_path}")

    def download(self):
        self.log.debug(f"Download feedback for {quote_plus(self.coursedir.notebook_id)} from {self.service_url}")
        r = self.api_request(
            f"feedback?course_id={quote_plus(self.coursedir.course_id)}&assignment_id={quote_plus(self.coursedir.assignment_id)}"  # noqa E501
        )
        self.log.debug(f"Got back {r.status_code} {r.headers['content-type']} after file download")
        content = r.json()

        # Feedback, here, is the time the feedback was generated, not the time of the submission
        if "feedback" in content:
            for f in content["feedback"]:
                self.log.debug(f"##### fetch-feedback.download has {f['filename']}, {f['timestamp']}")
                try:
                    # This matches nb_timestamp in list.parse_assignments, "status" == "submitted"
                    # The format should match the nbgrader default "%Y-%m-%d %H:%M:%S.%f %Z"
                    # timestamp = (
                    #     parser.parse(str(f["timestamp"]))
                    #     .strftime(self.timestamp_format)
                    #     .strip()
                    # )
                    timestamp = f["timestamp"]
                    os.makedirs(os.path.join(self.dest_path, timestamp), exist_ok=True)
                    self.log.debug(
                        f"##### fetch-feedback.download writing to {os.path.join(self.dest_path, timestamp)}"
                    )
                    with open(os.path.join(self.dest_path, timestamp, f["filename"]), "wb") as handle:
                        handle.write(base64.b64decode(f["content"]))
                except Exception as e:  # TODO: exception handling
                    self.fail(str(e))
        else:
            self.fail(content.get("note", "could not get feedback"))

    def copy_files(self):

        self.log.debug(f"Destination: {self.dest_path}")
        self.download()
        self.log.debug(f"Fetched as: {self.coursedir.notebook_id}")
