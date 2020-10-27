import io
import logging
import os
import shutil
import tarfile
from os.path import basename
from shutil import copyfile

import pytest

from mock import patch

from nbexchange.plugin import ExchangeSubmit, Exchange
from nbgrader.coursedir import CourseDirectory

from nbexchange.tests.utils import get_feedback_file
from nbgrader.exchange import ExchangeError
from nbgrader.utils import make_unique_key, notebook_hash


logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


feedback1_filename = os.path.join(
    os.path.dirname(__file__), "data", "assignment-0.6.html"
)
feedback1_file = get_feedback_file(feedback1_filename)
feedback2_filename = os.path.join(
    os.path.dirname(__file__), "data", "assignment-0.6-2.html"
)
feedback12_file = get_feedback_file(feedback1_filename)

notebook1_filename = os.path.join(
    os.path.dirname(__file__), "data", "assignment-0.6.ipynb"
)
notebook1_file = get_feedback_file(notebook1_filename)
notebook2_filename = os.path.join(
    os.path.dirname(__file__), "data", "assignment-0.6-2.ipynb"
)
notebook2_file = get_feedback_file(notebook2_filename)


@pytest.mark.gen_test
def test_submit_fetch_one(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"
        plugin_config.CourseDirectory.assignment_id = "assign_1_1"

        os.makedirs("assign_1_1", exist_ok=True)
        copyfile(
            notebook1_filename, os.path.join("assign_1_1", basename(notebook1_filename))
        )

        plugin = ExchangeSubmit(
            coursedir=CourseDirectory(config=plugin_config), config=plugin_config
        )

        def api_request(*args, **kwargs):
            if args[0].startswith("assignments"):
                return type(
                    "Request",
                    (object,),
                    {
                        "status_code": 200,
                        "json": (
                            lambda: {
                                "success": True,
                                "value": [
                                    {
                                        "assignment_id": "assign_1_1",
                                        "student_id": "1",
                                        "course_id": "no_course",
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "name": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": False,
                                            }
                                        ],
                                        "timestamp": "2020-01-01 00:00:00.0 UTC",
                                    }
                                ],
                            }
                        ),
                    },
                )
            else:
                pth = str(tmpdir.mkdir("submit_several").realpath())
                assert args[0] == (
                    f"submission?course_id=no_course&assignment_id=assign_1_1"
                )
                assert "method" not in kwargs or kwargs.get("method").lower() == "post"
                files = kwargs.get("files")
                assert "assignment" in files
                assert "assignment.tar.gz" == files["assignment"][0]
                tar_file = io.BytesIO(files["assignment"][1])
                with tarfile.open(fileobj=tar_file) as handle:
                    handle.extractall(path=pth)

                assert os.path.exists(os.path.join(pth, "assignment-0.6.ipynb"))
                assert os.path.exists(os.path.join(pth, "timestamp.txt"))
                return type(
                    "Request",
                    (object,),
                    {"status_code": 200, "json": (lambda: {"success": True})},
                )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
    finally:
        shutil.rmtree("assign_1_1")


@pytest.mark.gen_test
def test_submit_fetch_fail(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"
        plugin_config.CourseDirectory.assignment_id = "assign_1_2"

        os.makedirs("assign_1_2", exist_ok=True)
        copyfile(
            notebook1_filename, os.path.join("assign_1_2", basename(notebook1_filename))
        )

        plugin = ExchangeSubmit(
            coursedir=CourseDirectory(config=plugin_config), config=plugin_config
        )

        def api_request(*args, **kwargs):
            if args[0].startswith("assignments"):
                return type(
                    "Request",
                    (object,),
                    {
                        "status_code": 200,
                        "json": (
                            lambda: {
                                "success": True,
                                "value": [
                                    {
                                        "assignment_id": "assign_1_2",
                                        "student_id": "1",
                                        "course_id": "no_course",
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "name": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": False,
                                            }
                                        ],
                                        "timestamp": "2020-01-01 00:00:00.0 UTC",
                                    }
                                ],
                            }
                        ),
                    },
                )
            else:
                assert args[0] == (
                    f"submission?course_id=no_course&assignment_id=assign_1_2"
                )
                assert "method" not in kwargs or kwargs.get("method").lower() == "post"

                return type(
                    "Request",
                    (object,),
                    {
                        "status_code": 200,
                        "json": (lambda: {"success": False, "note": "failure note"}),
                    },
                )

        with pytest.raises(ExchangeError) as e_info, patch.object(
            Exchange, "api_request", side_effect=api_request
        ):
            called = plugin.start()
        assert str(e_info.value) == "failure note"
    finally:
        shutil.rmtree("assign_1_2")


@pytest.mark.gen_test
def test_submit_fetch_several(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = "assign_1_3"

    os.makedirs("assign_1_3", exist_ok=True)
    copyfile(
        notebook1_filename, os.path.join("assign_1_3", basename(notebook1_filename))
    )
    copyfile(
        notebook2_filename, os.path.join("assign_1_3", basename(notebook2_filename))
    )

    plugin = ExchangeSubmit(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )
    try:

        def api_request(*args, **kwargs):
            if args[0].startswith("assignments"):
                return type(
                    "Request",
                    (object,),
                    {
                        "status_code": 200,
                        "json": (
                            lambda: {
                                "success": True,
                                "value": [
                                    {
                                        "assignment_id": "assign_1_3",
                                        "student_id": "1",
                                        "course_id": "no_course",
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "name": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": False,
                                            },
                                            {
                                                "name": "assignment-0.6-2",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": False,
                                            },
                                        ],
                                        "timestamp": "2020-01-01 00:00:00.0 UTC",
                                    }
                                ],
                            }
                        ),
                    },
                )
            else:
                pth = str(tmpdir.mkdir("submit_several").realpath())
                assert args[0] == (
                    f"submission?course_id=no_course&assignment_id=assign_1_3"
                )
                assert "method" not in kwargs or kwargs.get("method").lower() == "post"
                files = kwargs.get("files")
                assert "assignment" in files
                assert "assignment.tar.gz" == files["assignment"][0]
                tar_file = io.BytesIO(files["assignment"][1])
                with tarfile.open(fileobj=tar_file) as handle:
                    handle.extractall(path=pth)

                assert os.path.exists(os.path.join(pth, "assignment-0.6.ipynb"))
                assert os.path.exists(os.path.join(pth, "assignment-0.6-2.ipynb"))
                assert os.path.exists(os.path.join(pth, "timestamp.txt"))
                return type(
                    "Request",
                    (object,),
                    {"status_code": 200, "json": (lambda: {"success": True})},
                )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
    finally:
        shutil.rmtree("assign_1_3")
