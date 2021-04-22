import datetime
import logging
import os
import sys
from shutil import copyfile

import pytest
import requests
from mock import patch
from nbgrader.coursedir import CourseDirectory
from nbgrader.exchange import ExchangeError
from nbgrader.utils import make_unique_key, notebook_hash

import nbexchange
from nbexchange.plugin import Exchange, ExchangeReleaseAssignment
from nbexchange.tests.utils import get_feedback_file

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


notebook1_filename = os.path.join(
    os.path.dirname(__file__), "data", "assignment-0.6.ipynb"
)
notebook1_file = get_feedback_file(notebook1_filename)
notebook2_filename = os.path.join(
    os.path.dirname(__file__), "data", "assignment-0.6-2.ipynb"
)
notebook2_file = get_feedback_file(notebook2_filename)


@pytest.mark.gen_test
def test_release_assignment_normal(plugin_config, tmpdir):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.release_directory = str(
        tmpdir.mkdir("submitted_test").realpath()
    )
    plugin_config.CourseDirectory.assignment_id = "assign_1"
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1"),
        exist_ok=True,
    )
    copyfile(
        notebook1_filename,
        os.path.join(
            plugin_config.CourseDirectory.release_directory, "assign_1", "release.ipynb"
        ),
    )
    with open(
        os.path.join(
            plugin_config.CourseDirectory.release_directory, "assign_1", "timestamp.txt"
        ),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    plugin = ExchangeReleaseAssignment(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    def api_request(*args, **kwargs):
        assert args[0] == (f"assignment?course_id=no_course" f"&assignment_id=assign_1")
        assert kwargs.get("method").lower() == "post"
        assert kwargs.get("data").get("notebooks") == ["release"]
        assert "assignment" in kwargs.get("files")
        assert "assignment.tar.gz" == kwargs.get("files").get("assignment")[0]
        assert len(kwargs.get("files").get("assignment")[1]) > 0

        return type(
            "Request",
            (object,),
            {"status_code": 200, "json": (lambda: {"success": True})},
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()


@pytest.mark.gen_test
def test_release_assignment_several_normal(plugin_config, tmpdir):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.release_directory = str(
        tmpdir.mkdir("submitted_test").realpath()
    )
    plugin_config.CourseDirectory.assignment_id = "assign_1"
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1"),
        exist_ok=True,
    )
    copyfile(
        notebook1_filename,
        os.path.join(
            plugin_config.CourseDirectory.release_directory,
            "assign_1",
            "release1.ipynb",
        ),
    )
    with open(
        os.path.join(
            plugin_config.CourseDirectory.release_directory, "assign_1", "timestamp.txt"
        ),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    copyfile(
        notebook1_filename,
        os.path.join(
            plugin_config.CourseDirectory.release_directory,
            "assign_1",
            "release1.ipynb",
        ),
    )

    copyfile(
        notebook2_filename,
        os.path.join(
            plugin_config.CourseDirectory.release_directory,
            "assign_1",
            "release2.ipynb",
        ),
    )

    plugin = ExchangeReleaseAssignment(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    def api_request(*args, **kwargs):
        assert args[0] == (f"assignment?course_id=no_course" f"&assignment_id=assign_1")
        assert kwargs.get("method").lower() == "post"
        assert kwargs.get("data").get("notebooks") == ["release1", "release2"]
        assert "assignment" in kwargs.get("files")
        assert "assignment.tar.gz" == kwargs.get("files").get("assignment")[0]
        assert len(kwargs.get("files").get("assignment")[1]) > 0

        return type(
            "Request",
            (object,),
            {"status_code": 200, "json": (lambda: {"success": True})},
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()


@pytest.mark.gen_test
def test_release_assignment_fail(plugin_config, tmpdir):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.release_directory = str(
        tmpdir.mkdir("submitted_test").realpath()
    )
    plugin_config.CourseDirectory.assignment_id = "assign_1"
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1"),
        exist_ok=True,
    )
    copyfile(
        notebook1_filename,
        os.path.join(
            plugin_config.CourseDirectory.release_directory,
            "assign_1",
            "feedback.ipynb",
        ),
    )
    with open(
        os.path.join(
            plugin_config.CourseDirectory.release_directory, "assign_1", "timestamp.txt"
        ),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    plugin = ExchangeReleaseAssignment(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    def api_request(*args, **kwargs):
        return type(
            "Request",
            (object,),
            {
                "status_code": 200,
                "json": (lambda: {"success": False, "note": "failure note"}),
            },
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        with pytest.raises(ExchangeError) as e_info:
            called = plugin.start()
        assert str(e_info.value) == "failure note"
