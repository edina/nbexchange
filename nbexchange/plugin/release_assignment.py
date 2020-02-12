import glob
import io
import json

import os

from .exchange import Exchange
from urllib.parse import quote_plus
import nbgrader.exchange.abc as abc


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
        self.src_path = self.coursedir.format_path(
            self.coursedir.release_directory, ".", self.coursedir.assignment_id
        )
        if not os.path.isdir(self.src_path):
            source = self.coursedir.format_path(
                self.coursedir.source_directory, ".", self.coursedir.assignment_id
            )
            if os.path.isdir(source):
                # Looks like the instructor forgot to assign
                self.fail(
                    "Assignment found in '{source}' but not '{self.src_path}', run `nbgrader assign` first."
                )
            else:
                self._assignment_not_found(
                    self.src_path,
                    self.coursedir.format_path(
                        self.coursedir.release_directory, ".", "*"
                    ),
                )
        self.log.debug(f"ExchangeRelease.init_src ensuring {self.src_path} exists")

    def init_dest(self):
        pass

    def tar_source(self):

        import tarfile

        tar_file = io.BytesIO()

        with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
            tar_handle.add(self.src_path, arcname=".")
        tar_file.seek(0)
        return tar_file.read()

    def get_notebooks(self):
        notebooks = []
        for notebook in sorted(glob.glob(os.path.join(self.src_path, "*.ipynb"))):
            notebooks.append(os.path.splitext(os.path.split(notebook)[1])[0])
        self.log.info(f"Found {len(notebooks)} notebooks: \n{notebooks}")
        self.notebooks = notebooks

    def upload(self, file):
        files = {"assignment": ("assignment.tar.gz", file)}

        url = f"assignment?course_id={quote_plus(self.course_id)}&assignment_id={quote_plus(self.coursedir.assignment_id)}"

        r = self.api_request(
            url, method="POST", data={"notebooks": self.notebooks}, files=files
        )
        self.log.debug(f"Got back {r.status_code} after file upload")

        try:
            data = r.json()
        except json.decoder.JSONDecodeError:
            self.fail(r.text)

        if not data["success"]:
            self.fail(data["note"])

        self.log.info("Successfully uploaded released assignment.")

    def copy_files(self):
        # Grab files from hard drive
        file = self.tar_source()
        # Upload files to exchange
        self.get_notebooks()
        self.upload(file)
