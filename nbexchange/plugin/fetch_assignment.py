import glob
import io
import os
import shutil
import tarfile
import tempfile
from urllib.parse import quote_plus

import nbgrader.exchange.abc as abc
from nbgrader.api import new_uuid
from traitlets import Bool

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
        self.log.debug(
            f"ExchangeFetch.init_src using {self.course_id} {self.coursedir.assignment_id}"
        )

        location = os.path.join(
            "/tmp/",
            new_uuid(),
            self.course_id,
            self.coursedir.assignment_id,
            "assignment.tar.gz",
        )
        os.makedirs(os.path.dirname(location), exist_ok=True)
        self.src_path = location
        self.log.debug(f"ExchangeFetch.init_src ensuring {self.src_path}")

    # where in the user tree
    def init_dest(self):
        if self.path_includes_course:
            root = os.path.join(self.course_id, self.coursedir.assignment_id)
        else:
            root = self.coursedir.assignment_id
        self.dest_path = os.path.abspath(os.path.join(self.assignment_dir, root))
        # Lets check there are no notebooks already in the dest_path dir
        if (
            os.path.isdir(self.dest_path)
            and glob.glob(self.dest_path + "/*.ipynb")
            and not self.replace_missing_files
        ):
            self.fail(
                f"You already have notebook documents in directory: {root}. Please remove them before fetching again"
            )
        else:
            os.makedirs(os.path.dirname(self.dest_path + "/"), exist_ok=True)
        self.log.debug(f"ExchangeFetch.init_dest ensuring {self.dest_path}")

    def download(self):
        self.log.debug(f"Download from {self.service_url}")
        r = self.api_request(
            f"assignment?course_id={quote_plus(self.course_id)}&assignment_id={quote_plus(self.coursedir.assignment_id)}"
        )
        self.log.debug(
            f"Got back {r.status_code}  {r.headers['content-type']} after file download"
        )
        # tgz = r.content

        # try:
        #     tar_file = io.BytesIO(tgz)
        #     with tarfile.open(fileobj=tar_file) as handle:
        #         handle.extractall(path=self.src_path)
        # except Exception as e:  # TODO: exception handling
        #     self.fail(str(e))
        if r.status_code > 399:
            self.fail(
                f"Error failing to fetch assignment {self.coursedir.assignment_id} on course {self.course_id}: status code {r.status_code}: error {r.content}"
            )

        if r.headers["content-type"] == "application/x-tar":
            tgz = r.content

            try:
                tar_file = io.BytesIO(tgz)
                with tarfile.open(fileobj=tar_file) as handle:
                    handle.extractall(path=self.src_path)
            except Exception as e:  # TODO: exception handling
                if hasattr(e, "message"):
                    self.fail(
                        f"Error unpacking download for {self.coursedir.assignment_id} on course {self.course_id}: {e.message}"
                    )
                else:
                    self.fail(
                        f"Error unpacking download for {self.coursedir.assignment_id} on course {self.course_id}: {e}"
                    )
        else:
            # Fails, even if the json response is a success (for now)
            data = r.json()
            if not data["success"]:
                self.fail(
                    f"Error failing to fetch assignment {self.coursedir.assignment_id} on course {self.course_id}"
                )
            else:
                self.fail(
                    f"Error failing to fetch assignment {self.coursedir.assignment_id} on course {self.course_id}: {data['note']}"
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
                    self.log.warning("Creating missing directory '%s'", relpath)
                    os.mkdir(destpath)

                else:
                    self.log.warning("Replacing missing file '%s'", relpath)
                    shutil.copy(srcpath, destpath)

            if os.path.isdir(srcpath):
                self.copy_if_missing(srcpath, destpath, ignore=ignore)

    def do_copy(self, src, dest):
        """Copy the src dir to the dest dir omitting the self.coursedir.ignore globs."""
        self.download()
        if os.path.isdir(self.dest_path):
            self.copy_if_missing(
                src, dest, ignore=shutil.ignore_patterns(*self.coursedir.ignore)
            )
        else:
            shutil.copytree(
                src, dest, ignore=shutil.ignore_patterns(*self.coursedir.ignore)
            )
        # clear tmp having downloaded file
        shutil.rmtree(self.src_path)

    def copy_files(self):
        self.log.debug(f"Source: {self.src_path}")
        self.log.debug(f"Destination: {self.dest_path}")
        self.do_copy(self.src_path, self.dest_path)
        self.log.debug(f"Fetched as: {self.course_id} {self.coursedir.assignment_id}")
