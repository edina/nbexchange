import asyncio
import base64
import datetime
import io
import os
import tarfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from functools import partial

import pytest
import requests
from dateutil.tz import gettz

from nbexchange.app import NbExchange
from nbexchange.models.actions import Action
from nbexchange.models.assignments import Assignment as AssignmentModel
from nbexchange.models.courses import Course
from nbexchange.models.feedback import Feedback
from nbexchange.models.notebooks import Notebook
from nbexchange.models.subscriptions import Subscription
from nbexchange.models.users import User

# These replicate what's defined in nbexchange/app.py, nbexchange/handlers/base.py.... and nbgrader/exchange/exchange.py
n = NbExchange()
time_zone = n.timezone
timestamp_format = n.timestamp_format
tz = gettz(time_zone)

#####
#
# Check in handlers.auth.naas_user_handlers.NaasUserHandler - username.replace("_", "-", 1)
#
user_kiz = {"name": "1-kiz"}
user_bert = {"name": "1-bert"}

user_kiz_instructor = {
    "id": 1,
    "name": "1-kiz",
    "course_id": "course_2",
    "course_role": "Instructor",
    "course_title": "A title",
}

user_kiz_student = {
    "id": 1,
    "name": "1-kiz",
    "course_id": "course_2",
    "course_role": "Student",
    "course_title": "A title",
}

user_zik_student = {
    "id": 2,
    "name": "1-zik",
    "course_id": "course_2",
    "course_role": "Student",
    "course_title": "A title",
    "full_name": "One Zik",
    "email": "zik@example.com",
    "lms_user_id": "zik",
}

user_brobbere_instructor = {
    "id": 3,
    "name": "1-brobbere",
    "course_id": "course_2",
    "course_role": "Instructor",
    "course_title": "A title",
}

user_brobbere_student = {
    "id": 3,
    "name": "1-brobbere",
    "course_id": "course_2",
    "course_role": "Student",
}

user_lkihlman_instructor = {
    "id": 4,
    "name": "1-lkihlman",
    "course_id": "course_1",
    "course_role": "Instructor",
    "course_title": "Another title",
}

user_lkihlman_student = {
    "id": 4,
    "name": "1-lkihlman",
    "course_id": "course_1",
    "course_role": "Student",
}


def tar_source(filename):
    import tarfile

    tar_file = io.BytesIO()

    with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
        tar_handle.add(filename, arcname=".")
    tar_file.seek(0)
    return tar_file.read()


def api_request(self, url, method="GET", *args, **kwargs):
    headers = {}

    if method == "GET":
        get_req = partial(requests.get, url, headers=headers)
        return get_req(*args, **kwargs)
    elif method == "POST":
        post_req = partial(requests.post, url, headers=headers)
        return post_req(*args, **kwargs)
    elif method == "DELETE":
        delete_req = partial(requests.delete, url, headers=headers)
        return delete_req(*args, **kwargs)
    else:
        raise NotImplementedError(f"HTTP Method {method} is not implemented")


def get_files_dict():

    timestamp = datetime.datetime.now(tz).strftime(timestamp_format).strip()

    notebooks = ["assignment-0.6", "assignment-0.6-2"]

    # notebook 1
    notebook1_filename = os.path.join(os.path.dirname(__file__), "data", f"{notebooks[0]}.ipynb")

    # notebook 2
    notebook2_filename = os.path.join(os.path.dirname(__file__), "data", f"{notebooks[1]}.ipynb")

    tar_file = io.BytesIO()
    with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:

        arcname = os.path.relpath(notebook1_filename, start=os.path.dirname(__file__))
        tar_handle.add(notebook1_filename, arcname=arcname)
        arcname = os.path.relpath(notebook2_filename, start=os.path.dirname(__file__))
        tar_handle.add(notebook2_filename, arcname=arcname)

        with closing(io.BytesIO(timestamp.encode())) as fobj:
            tarinfo = tarfile.TarInfo("timestamp.txt")
            tarinfo.size = len(fobj.getvalue())
            tarinfo.mtime = time.time()
            tar_handle.addfile(tarinfo, fileobj=fobj)

    tar_file.seek(0)
    tar_file = tar_file.read()
    files = {"assignment": ("assignment.tar.gz", tar_file)}
    return files, notebooks, timestamp


def get_feedback_dict(filename):
    with open(filename) as feedback_file:
        files = {"feedback": ("feedback.html", feedback_file.read())}
    return files


def get_feedback_file(filename):
    with open(filename, "rb") as feedback_file:
        files = base64.b64encode(feedback_file.read())
    return files


class _AsyncRequests:
    """Wrapper around requests to return a Future from request methods
    A single thread is allocated to avoid blocking the IOLoop thread.
    """

    def __init__(self):
        self.executor = ThreadPoolExecutor(1)
        real_submit = self.executor.submit
        self.executor.submit = lambda *args, **kwargs: asyncio.wrap_future(real_submit(*args, **kwargs))

    def __getattr__(self, name):
        requests_method = getattr(requests, name)
        return lambda *args, **kwargs: self.executor.submit(requests_method, *args, **kwargs)


# async_requests.get = requests.get returning a Future, etc.
async_requests = _AsyncRequests()


class AsyncSession(requests.Session):
    """requests.Session object that runs in the background thread"""

    def request(self, *args, **kwargs):
        return async_requests.executor.submit(super().request, *args, **kwargs)


# fixture to clear the database completely
@pytest.fixture
def clear_database(db):
    """Clears the database.

    requires the db handler
    """
    db.query(Action).delete()
    db.query(AssignmentModel).delete()
    db.query(Course).delete()
    db.query(Feedback).delete()
    db.query(Notebook).delete()
    db.query(Subscription).delete()
    db.query(User).delete()
