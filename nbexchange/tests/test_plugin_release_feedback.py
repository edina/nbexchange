import logging
import os
from shutil import copyfile

import pytest

from mock import patch

from nbexchange.plugin import ExchangeReleaseFeedback, Exchange
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
def test_release_feedback_fetch_normal(plugin_config, tmpdir):
    plugin_config.CourseDirectory.root = "/"
    plugin_config.CourseDirectory.feedback_directory = str(
        tmpdir.mkdir("feedback_test").realpath()
    )
    plugin_config.CourseDirectory.submitted_directory = str(
        tmpdir.mkdir("submitted_test").realpath()
    )
    plugin_config.CourseDirectory.assignment_id = "assign_1"
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.feedback_directory, "1", "assign_1"),
        exist_ok=True,
    )
    os.makedirs(
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory, "1", "assign_1"
        ),
        exist_ok=True,
    )

    feedback_filename_uploaded = os.path.join(
        plugin_config.CourseDirectory.feedback_directory,
        "1",
        "assign_1",
        "feedback.html",
    )
    copyfile(feedback1_filename, feedback_filename_uploaded)

    copyfile(
        notebook1_filename,
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory,
            "1",
            "assign_1",
            "feedback.ipynb",
        ),
    )
    with open(
        os.path.join(
            plugin_config.CourseDirectory.feedback_directory,
            "1",
            "assign_1",
            "timestamp.txt",
        ),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    unique_key = make_unique_key(
        "no_course", "assign_1", "feedback", "1", "2020-01-01 00:00:00.0 UTC"
    )
    checksum = notebook_hash(
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory,
            "1",
            "assign_1",
            "feedback.ipynb",
        ),
        unique_key,
    )

    plugin = ExchangeReleaseFeedback(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    def api_request(*args, **kwargs):
        assert args[0] == (
            "feedback?course_id=no_course"
            "&assignment_id=assign_1"
            "&notebook=feedback"
            "&student=1"
            "&timestamp=2020-01-01T00%3A00%3A00"
            "&checksum=" + checksum
        )
        assert kwargs.get("method").lower() == "post"
        assert "feedback" in kwargs.get("files")
        assert ("feedback.html", open(feedback_filename_uploaded).read()) == kwargs.get(
            "files"
        ).get("feedback")
        return type(
            "Request",
            (object,),
            {"status_code": 200, "json": (lambda: {"success": True})},
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()


@pytest.mark.gen_test
def test_release_feedback_fetch_several_normal(plugin_config, tmpdir):
    feedback_directory = str(tmpdir.mkdir("feedback_test").realpath())
    submitted_directory = str(tmpdir.mkdir("submitted_test").realpath())
    plugin_config.CourseDirectory.root = "/"
    plugin_config.CourseDirectory.feedback_directory = feedback_directory
    plugin_config.CourseDirectory.submitted_directory = submitted_directory
    plugin_config.CourseDirectory.assignment_id = "assign_1"
    os.makedirs(os.path.join(feedback_directory, "1", "assign_1"), exist_ok=True)
    os.makedirs(os.path.join(submitted_directory, "1", "assign_1"), exist_ok=True)
    feedback1_filename_uploaded = os.path.join(
        feedback_directory, "1", "assign_1", "feedback1.html"
    )
    copyfile(feedback1_filename, feedback1_filename_uploaded)
    copyfile(
        notebook1_filename,
        os.path.join(submitted_directory, "1", "assign_1", "feedback1.ipynb"),
    )

    feedback2_filename_uploaded = os.path.join(
        feedback_directory, "1", "assign_1", "feedback2.html"
    )
    copyfile(feedback2_filename, feedback2_filename_uploaded)
    copyfile(
        notebook2_filename,
        os.path.join(submitted_directory, "1", "assign_1", "feedback2.ipynb"),
    )

    unique_key1 = make_unique_key(
        "no_course", "assign_1", "feedback1", "1", "2020-01-01 00:01:00.0 UTC"
    )
    checksum1 = notebook_hash(
        os.path.join(submitted_directory, "1", "assign_1", "feedback1.ipynb"),
        unique_key1,
    )
    unique_key2 = make_unique_key(
        "no_course", "assign_1", "feedback2", "1", "2020-01-01 00:01:00.0 UTC"
    )
    checksum2 = notebook_hash(
        os.path.join(submitted_directory, "1", "assign_1", "feedback2.ipynb"),
        unique_key2,
    )

    with open(
        os.path.join(feedback_directory, "1", "assign_1", "timestamp.txt"), "w"
    ) as fp:
        fp.write("2020-01-01 00:01:00.0 UTC")

    plugin = ExchangeReleaseFeedback(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )
    seen_feedback1 = False
    seen_feedback2 = False

    def api_request(*args, **kwargs):
        nonlocal seen_feedback1, seen_feedback2
        if "feedback1" in args[0]:
            assert seen_feedback1 is False
            seen_feedback1 = True
            assert args[0] == (
                "feedback?course_id=no_course"
                "&assignment_id=assign_1"
                "&notebook=feedback1"
                "&student=1"
                "&timestamp=2020-01-01T00%3A01%3A00"
                "&checksum=" + checksum1
            )
            assert kwargs.get("method").lower() == "post"
            assert "feedback" in kwargs.get("files")
            assert (
                "feedback.html",
                open(feedback1_filename_uploaded).read(),
            ) == kwargs.get("files").get("feedback")

        elif "feedback2" in args[0]:
            assert seen_feedback2 is False
            seen_feedback2 = True
            assert args[0] == (
                "feedback?course_id=no_course"
                "&assignment_id=assign_1"
                "&notebook=feedback2"
                "&student=1"
                "&timestamp=2020-01-01T00%3A01%3A00"
                "&checksum=" + checksum2
            )
            assert kwargs.get("method").lower() == "post"
            assert "feedback" in kwargs.get("files")
            assert (
                "feedback.html",
                open(feedback2_filename_uploaded).read(),
            ) == kwargs.get("files").get("feedback")
        else:
            assert False
        return type(
            "Request",
            (object,),
            {"status_code": 200, "json": (lambda: {"success": True})},
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()
        assert seen_feedback1 and seen_feedback2


@pytest.mark.gen_test
def test_release_feedback_fetch_fail(plugin_config, tmpdir):
    plugin_config.CourseDirectory.root = "/"
    plugin_config.CourseDirectory.feedback_directory = str(
        tmpdir.mkdir("feedback_test").realpath()
    )
    plugin_config.CourseDirectory.submitted_directory = str(
        tmpdir.mkdir("submitted_test").realpath()
    )
    plugin_config.CourseDirectory.assignment_id = "assign_1"
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.feedback_directory, "1", "assign_1"),
        exist_ok=True,
    )
    os.makedirs(
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory, "1", "assign_1"
        ),
        exist_ok=True,
    )

    feedback_filename_uploaded = os.path.join(
        plugin_config.CourseDirectory.feedback_directory,
        "1",
        "assign_1",
        "feedback.html",
    )
    copyfile(feedback1_filename, feedback_filename_uploaded)

    copyfile(
        notebook1_filename,
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory,
            "1",
            "assign_1",
            "feedback.ipynb",
        ),
    )
    with open(
        os.path.join(
            plugin_config.CourseDirectory.feedback_directory,
            "1",
            "assign_1",
            "timestamp.txt",
        ),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    plugin = ExchangeReleaseFeedback(
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
