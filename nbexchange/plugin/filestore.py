import io
import json
import os
import tarfile
import tempfile
from functools import partial
from urllib.parse import quote_plus, urljoin

import requests
from nbgrader.exchange import ExchangeError
from traitlets.config import LoggingConfigurable, Unicode

from nbexchange_code.nbexchange.plugin.util import get_files


class FileStore:
    def load_file(self, file, **details):
        pass

    def store_file(self, file, content, **details):
        pass

    def delete_file(self, file, **details):
        pass

    def list_files(self, **details):
        pass

    def load_files(self, files, **details):
        return {file: self.load_file(file, **details) for file in files}

    def store_files(self, files, **details):
        for file, content in files.items():
            self.store_file(file, content, **details)

    def delete_files(self, files, **details):
        for file in files:
            self.delete_file(file, **details)

    @classmethod
    def copy_files(cls, fs1, fs2, **details):
        for f_details in fs1.list_files(**details):
            file = f_details["name"]
            deets = f_details["details"]
            content = fs1.load_file(file, binary=True, **deets)
            fs2.store_file(file, content, binary=True, **deets)


class LocalFileStore:
    def __init__(self, root, path_format):
        self.root = root
        self.path_format = path_format

    def load_file(self, file, binary=False, **details):
        directory = self.path_format.format(**details)
        full_path = os.path.join(directory, file)
        with open(full_path, "r" if not binary else "rb") as fp:
            return fp.read()

    def store_file(self, file, content, binary=False, **details):
        directory = self.path_format.format(**details)
        full_path = os.path.join(directory, file)
        with open(full_path, "w" if not binary else "wb") as fp:
            return fp.write(content)

    def delete_file(self, file, **details):
        directory = self.path_format.format(**details)
        full_path = os.path.join(directory, file)
        if os.path.isdir(full_path):
            os.removedirs(full_path)
        else:
            os.remove(full_path)

    def list_files(self, **details):
        return get_files(self.root, self.path_format, **details)


class RemoteFileStore(FileStore, LoggingConfigurable):
    def __init__(self, service_url, tmp_dir=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service_url = service_url
        self.endpoints = {
            "source": "assignment?course_id={course_id}&assignment_id={assignment_id}",
            "release": "assignments?course_id={course_id}&assignment_id={assignment_id}",
            "submitted": "feedback?course_id={course_id}&assignment_id={assignment_id}",
            "autograded": "collections?course_id={course_id}&assignment_id={assignment_id}",
            "feedback": "submit?course_id={course_id}&assignment_id={assignment_id}",
        }
        if tmp_dir is None:
            tmp_dir = tempfile.mkdtemp()
        self.tmp_dir = tmp_dir

    def fail(self, msg):
        self.log.fatal(msg)
        raise ExchangeError(msg)

    def api_request(self, path, method="GET", *args, **kwargs):
        jwt_token = os.environ.get("NAAS_JWT")

        cookies = dict()
        headers = dict()

        if jwt_token:
            cookies["noteable_auth"] = jwt_token

        url = urljoin(self.service_url, path)

        self.log.info(f"RemoteFileStore.api_request calling exchange with url {url}")

        if method == "GET":
            request = partial(requests.get, url, headers=headers, cookies=cookies)
        elif method == "POST":
            request = partial(requests.post, url, headers=headers, cookies=cookies)
        elif method == "DELETE":
            request = partial(requests.delete, url, headers=headers, cookies=cookies)
        else:
            raise NotImplementedError(f"HTTP Method {method} is not implemented")
        return request(*args, **kwargs)

    def load_file(self, file, binary=False, **details):
        self.log.debug(f"Download from {self.service_url}")
        url = self.endpoints[details["nbgrader_step"]].format(**details)
        r = self.api_request(url)
        self.log.debug(
            f"Got back {r.status_code}  {r.headers['content-type']} after file download"
        )
        tgz = r.content
        # create this directory in a way that it can be cached for later use (so we don't need to keep downloading the same data)

        try:
            tar_file = io.BytesIO(tgz)
            with tarfile.open(fileobj=tar_file) as handle:
                handle.extractall(path=self.tmp_dir)
        except Exception as e:  # TODO: exception handling
            self.fail(str(e))
        full_path = os.path.join(self.tmp_dir, file)
        with open(full_path, "r" if not binary else "rb") as fp:
            return fp.read()

    def store_file(self, file, content, binary=False, **details):
        full_path = os.path.join(self.tmp_dir, file)

        try:
            tar_file = io.BytesIO(content)
            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(full_path, arcname=".")
            tar_file.seek(0)
        except Exception as e:  # TODO: exception handling
            self.fail(str(e))

        files = {"assignment": ("assignment.tar.gz", full_path)}

        url = self.endpoints[details["nbgrader_step"]].format(**details)

        r = self.api_request(
            url, method="POST", data={"notebooks": details["notebooks"]}, files=files
        )
        self.log.debug(f"Got back {r.status_code} after file upload")

        try:
            data = r.json()
        except json.decoder.JSONDecodeError:
            self.fail(r.text)

        if not data["success"]:
            self.fail(data["note"])

        self.log.info("Successfully uploaded released assignment.")

    def list_files(self, **details):
        # return get_files(self.root, self.path_format, **details)
        pass
