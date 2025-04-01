import glob
import io
import json
import os
import sys
from urllib.parse import quote_plus

import nbgrader.exchange.abc as abc
import requests

from .exchange import Exchange


class ExchangeReleaseAssignment(abc.ExchangeReleaseAssignment, Exchange):
    def do_copy(self, src, dest):
        pass

    src_path = None
    notebooks = None

    def _load_config(self, cfg, **kwargs):
        if "ExchangeReleaseAssignment" in cfg:
            self.log.warning(
                "Use ExchangeReleaseAssignment in config, not ExchangeRelease. Outdated config:\n%s",
                "\n".join(
                    "ExchangeRelease.{key} = {value!r}".format(key=key, value=value)
                    for key, value in cfg.GenerateFeedbackApp.items()
                ),
            )
            cfg.ExchangeReleaseAssignment.merge(cfg.ExchangeRelease)
            del cfg.ExchangeRelease

        super(ExchangeReleaseAssignment, self)._load_config(cfg, **kwargs)

    def init_src(self):
        self.src_path = self.coursedir.format_path(self.coursedir.release_directory, ".", self.coursedir.assignment_id)
        if not os.path.isdir(self.src_path):
            source = self.coursedir.format_path(self.coursedir.source_directory, ".", self.coursedir.assignment_id)
            if os.path.isdir(source):
                # Looks like the instructor forgot to assign
                self.fail(f"Assignment found in '{source}' but not '{self.src_path}', run `nbgrader assign` first.")
            else:
                self._assignment_not_found(
                    self.src_path,
                    self.coursedir.format_path(self.coursedir.release_directory, ".", "*"),
                )
        self.log.debug(f"ExchangeRelease.init_src ensuring {self.src_path} exists")

    # Unlike the filesystem version, we don't need to have an exchange folder
    # or `self.course_path` from the `default` exchange
    def init_dest(self):
        if self.coursedir.course_id == "":
            self.fail("No course id specified. Re-run with --course flag.")

    def tar_source(self):
        import tarfile

        tar_file = io.BytesIO()

        with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
            self.add_to_tar(tar_handle, self.src_path, self.ignore)
        tar_file.seek(0)
        return tar_file.read()

    def get_notebooks(self):
        notebooks = []
        for notebook in sorted(glob.glob(os.path.join(self.src_path, "*.ipynb"))):
            notebooks.append(os.path.splitext(os.path.split(notebook)[1])[0])
        self.log.debug(f"Found {len(notebooks)} notebooks: \n{notebooks}")
        self.notebooks = notebooks

    def upload(self, file):
        files = {"assignment": ("assignment.tar.gz", file)}
        self.log.info(f"Source: {self.src_path}")
        self.log.info("Destination: The exhange service")

        url = f"assignment?course_id={quote_plus(self.coursedir.course_id)}&assignment_id={quote_plus(self.coursedir.assignment_id)}"  # noqa: E501

        try:
            r = self.api_request(url, method="POST", data={"notebooks": self.notebooks}, files=files)
        except requests.exceptions.Timeout:
            self.fail("Timed out trying to reach the exchange service to release assignment.")

        self.log.debug(f"Got back {r.status_code} after file upload")

        # In theory, we should never hit this, as the file size _should_ be caught in `copy_files`
        if r.status_code == 400 and sys.getsizeof(file) > self.max_buffer_size:
            self.fail(
                f"Assignment {self.coursedir.assignment_id} not released. "
                "The contents of your assignment are too large:\n"
                "The total size of all files in the 'generated' directory, when compressed "
                f"using tar -czvf must be less than {self.max_buffer_size}.\n"
                "You may have large data files, temporary files, and/or working files that should not be included"
                " - try deleting them."
            )
        try:
            data = r.json()
        except json.decoder.JSONDecodeError as err:
            self.log.error("release_assignment failed upload\n" f"response text: {r.text}\n" f"JSONDecodeError: {err}")
            self.fail(r.text)

        if not data["success"]:
            self.fail(data["note"])

        self.log.info(f"Released as: {self.coursedir.course_id} {self.coursedir.assignment_id}")

    def copy_files(self):
        # Grab files from hard drive
        file = self.tar_source()
        if sys.getsizeof(file) > self.max_buffer_size:
            self.fail(
                f"Assignment {self.coursedir.assignment_id} not released. "
                "The contents of your assignment are too large:\n"
                "The total size of all files in the 'generated' directory, when compressed "
                f"using tar -czvf must be less than {self.max_buffer_size}.\n"
                "You may have large data files, temporary files, and/or working files that should not be included"
                " - try deleting them."
            )
        # Upload files to exchange
        self.get_notebooks()
        self.upload(file)
