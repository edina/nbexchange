import glob
import io
import json
import os
import shutil
import tarfile
from urllib.parse import quote_plus

import nbgrader.exchange.abc as abc
import requests
from nbgrader.api import new_uuid

from .exchange import Exchange


class ExchangeFetchAssignment(abc.ExchangeFetchAssignment, Exchange):
    def _load_config(self, cfg, **kwargs):
        if "ExchangeFetch" in cfg:
            self.log.warning(
                "Use ExchangeFetchAssignment in config, not ExchangeFetch. Outdated config:\n%s",
                "\n".join(
                    "ExchangeFetch.{key} = {value!r}".format(key=key, value=value)
                    for key, value in cfg.ExchangeFetch.items()
                ),
            )
            cfg.ExchangeFetchAssignment.merge(cfg.ExchangeFetch)
            del cfg.ExchangeFetch

        super(ExchangeFetchAssignment, self)._load_config(cfg, **kwargs)

    # where the downloaded files are placed
    def init_src(self):
        self.log.debug(f"ExchangeFetch.init_src using {self.coursedir.course_id} {self.coursedir.assignment_id}")

        location = os.path.join(
            "/tmp/",
            new_uuid(),
            self.coursedir.course_id,
            self.coursedir.assignment_id,
            "assignment.tar.gz",
        )
        os.makedirs(os.path.dirname(location), exist_ok=True)
        self.src_path = location
        self.log.debug(f"ExchangeFetch.init_src ensuring {self.src_path}")

    # where in the user tree
    def init_dest(self):
        if self.path_includes_course:
            root = os.path.join(self.coursedir.course_id, self.coursedir.assignment_id)
        else:
            root = self.coursedir.assignment_id
        self.dest_path = os.path.abspath(os.path.join(self.assignment_dir, root))
        # Lets check there are no notebooks already in the dest_path dir
        if os.path.isdir(self.dest_path) and glob.glob(self.dest_path + "/*.ipynb") and not self.replace_missing_files:
            self.fail(
                f"You already have notebook documents in directory: {root}. Please remove them before fetching again"
            )
        else:
            os.makedirs(os.path.dirname(self.dest_path + "/"), exist_ok=True)
        self.log.debug(f"ExchangeFetch.init_dest ensuring {self.dest_path}")

    def download(self):
        self.log.debug(f"Download from {self.service_url}")
        try:
            r = self.api_request(
                f"assignment?course_id={quote_plus(self.coursedir.course_id)}&assignment_id={quote_plus(self.coursedir.assignment_id)}"  # noqa: E501
            )
        except requests.exceptions.Timeout:
            self.fail("Timed out trying to reach the exchange service to fetch the assignment.")
        except Exception as err:
            self.fail(f"fetch_assignment failed: {err}")
        self.log.debug(f"Got back {r.status_code}  after file download")  # {r.headers['content-type']}

        if r.status_code > 399:
            self.fail(
                f"Error failing to fetch assignment {self.coursedir.assignment_id} on course {self.coursedir.course_id}: status code {r.status_code}: error {r.content}"  # noqa: E501
            )

        if r.headers["content-type"] == "application/gzip":
            tgz = r.content

            try:
                tar_file = io.BytesIO(tgz)
                with tarfile.open(fileobj=tar_file) as handle:
                    handle.extractall(path=self.src_path)
            except Exception as e:  # TODO: exception handling
                if hasattr(e, "message"):
                    self.fail(
                        f"Error unpacking download for {self.coursedir.assignment_id} on course {self.coursedir.course_id}: {e.message}"  # noqa: E501
                    )
                else:
                    self.fail(
                        f"Error unpacking download for {self.coursedir.assignment_id} on course {self.coursedir.course_id}: {e}"  # noqa: E501
                    )
        else:
            # Fails, even if the json response is a success (for now)
            try:
                data = r.json()
            except json.decoder.JSONDecodeError as err:
                self.log.error("fetch_assignment download\n" f"response text: {r.text}\n" f"JSONDecodeError: {err}")
                self.fail(r.text)
            if not data["success"]:
                self.fail(
                    f"Error failing to fetch assignment {self.coursedir.assignment_id} on course {self.coursedir.course_id}: message: {data.get('note')}"  # noqa: E501
                )
            else:
                self.fail(
                    f"Error failing to fetch assignment {self.coursedir.assignment_id} on course {self.coursedir.course_id}: {data.get('note')}"  # noqa: E501
                )

    def copy_if_missing(self, src, dest, ignore=None):
        filenames = sorted(os.listdir(src))
        if ignore:
            bad_filenames = ignore(src, filenames)
            filenames = sorted(list(set(filenames) - bad_filenames))

        for filename in filenames:
            srcpath = os.path.join(src, filename)
            destpath = os.path.join(dest, filename)
            relpath = os.path.relpath(destpath, os.getcwd())
            if not os.path.exists(destpath):
                if os.path.isdir(srcpath):
                    self.log.info("Creating missing directory '%s'", relpath)
                    os.mkdir(destpath)

                else:
                    self.log.info("Replacing missing file '%s'", relpath)
                    shutil.copy(srcpath, destpath)

            if os.path.isdir(srcpath):
                self.copy_if_missing(srcpath, destpath, ignore=ignore)

    def do_copy(self, src, dest):
        """Copy the src dir to the dest dir omitting the self.coursedir.ignore globs."""
        self.download()
        if os.path.isdir(self.dest_path):
            self.copy_if_missing(src, dest, ignore=shutil.ignore_patterns(*self.coursedir.ignore))
        else:
            shutil.copytree(src, dest, ignore=shutil.ignore_patterns(*self.coursedir.ignore))
        # clear tmp having downloaded file
        shutil.rmtree(self.src_path)

    def copy_files(self):
        self.log.debug(f"Source: {self.src_path}")
        self.log.info("Source: The exhange service")
        self.log.info(f"Destination: {self.dest_path}")
        self.do_copy(self.src_path, self.dest_path)
        self.log.info(f"Fetched as: {self.coursedir.course_id} {self.coursedir.assignment_id}")
