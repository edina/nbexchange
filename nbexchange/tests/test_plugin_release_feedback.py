import logging
import os
import re
from shutil import copyfile

import pytest
from mock import patch
from nbgrader.coursedir import CourseDirectory
from nbgrader.exchange import ExchangeError
from nbgrader.utils import make_unique_key, notebook_hash

from nbexchange.plugin import Exchange, ExchangeReleaseFeedback
from nbexchange.tests.utils import get_feedback_file

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


feedback1_filename = os.path.join(os.path.dirname(__file__), "data", "assignment-0.6.html")
feedback1_file = get_feedback_file(feedback1_filename)
feedback2_filename = os.path.join(os.path.dirname(__file__), "data", "assignment-0.6-2.html")
feedback12_file = get_feedback_file(feedback1_filename)

notebook1_filename = os.path.join(os.path.dirname(__file__), "data", "assignment-0.6.ipynb")
notebook1_file = get_feedback_file(notebook1_filename)
notebook2_filename = os.path.join(os.path.dirname(__file__), "data", "assignment-0.6-2.ipynb")
notebook2_file = get_feedback_file(notebook2_filename)

student_id = "1"
assignment_id = "assign_1"


@pytest.mark.gen_test
def test_release_feedback_methods(plugin_config, tmpdir):
    plugin_config.CourseDirectory.root = "/"
    plugin_config.CourseDirectory.feedback_directory = str(tmpdir.mkdir("feedback_test").realpath())
    plugin_config.CourseDirectory.assignment_id = assignment_id

    plugin = ExchangeReleaseFeedback(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
    plugin.init_src()
    print(f"asserting plugin.src_path: {plugin.src_path}")
    assert re.search(r"test_release_feedback_methods0/feedback_test/\*/assign_1$", plugin.src_path)
    plugin.coursedir.student_id = student_id
    plugin.init_src()
    assert re.search(r"test_release_feedback_methods0/feedback_test/1/assign_1$", plugin.src_path)

    with pytest.raises(ExchangeError) as e_info:
        plugin.init_dest()
        assert str(e_info.value) == "No course id specified. Re-run with --course flag."


@pytest.mark.gen_test
def test_release_feedback_fetch_normal(plugin_config, tmpdir):
    plugin_config.CourseDirectory.root = "/"
    plugin_config.CourseDirectory.feedback_directory = str(tmpdir.mkdir("feedback_test").realpath())
    plugin_config.CourseDirectory.submitted_directory = str(tmpdir.mkdir("submitted_test").realpath())
    plugin_config.CourseDirectory.assignment_id = assignment_id
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.feedback_directory, student_id, assignment_id),
        exist_ok=True,
    )
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.submitted_directory, student_id, assignment_id),
        exist_ok=True,
    )

    feedback_filename_uploaded = os.path.join(
        plugin_config.CourseDirectory.feedback_directory,
        student_id,
        assignment_id,
        "feedback.html",
    )
    copyfile(feedback1_filename, feedback_filename_uploaded)

    copyfile(
        notebook1_filename,
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory,
            student_id,
            assignment_id,
            "feedback.ipynb",
        ),
    )
    with open(
        os.path.join(
            plugin_config.CourseDirectory.feedback_directory,
            student_id,
            assignment_id,
            "timestamp.txt",
        ),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    unique_key = make_unique_key("no_course", assignment_id, "feedback", student_id, "2020-01-01 00:00:00.0 UTC")
    checksum = notebook_hash(
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory,
            student_id,
            assignment_id,
            "feedback.ipynb",
        ),
        unique_key,
    )

    plugin = ExchangeReleaseFeedback(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    def api_request(*args, **kwargs):
        assert args[0] == (
            "feedback?course_id=no_course"
            f"&assignment_id={assignment_id}"
            "&notebook=feedback"
            f"&student={student_id}"
            "&timestamp=2020-01-01+00%3A00%3A00.0+UTC"
            "&checksum=" + checksum
        )
        assert kwargs.get("method").lower() == "post"
        assert "feedback" in kwargs.get("files")
        assert ("feedback.html", open(feedback_filename_uploaded).read()) == kwargs.get("files").get("feedback")
        return type(
            "Request",
            (object,),
            {"status_code": 200, "json": (lambda: {"success": True})},
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        plugin.start()


@pytest.mark.gen_test
def test_release_feedback_fetch_several_normal(plugin_config, tmpdir):
    # set up the submitted & feeback directories
    feedback_directory = str(tmpdir.mkdir("feedback_test").realpath())
    submitted_directory = str(tmpdir.mkdir("submitted_test").realpath())
    plugin_config.CourseDirectory.root = "/"
    plugin_config.CourseDirectory.feedback_directory = feedback_directory
    plugin_config.CourseDirectory.submitted_directory = submitted_directory
    plugin_config.CourseDirectory.assignment_id = assignment_id
    os.makedirs(os.path.join(feedback_directory, student_id, assignment_id), exist_ok=True)
    os.makedirs(os.path.join(submitted_directory, student_id, assignment_id), exist_ok=True)

    # Scenario:
    # two pieces of feedback for two notebooks, for the same submission
    # * submitted_directory is where the student .ipynb file was collected into
    # * feedback_directory is where the generated .html feeback was written to
    feedback1_filename_uploaded = os.path.join(feedback_directory, student_id, assignment_id, "feedback1.html")
    copyfile(feedback1_filename, feedback1_filename_uploaded)
    copyfile(
        notebook1_filename,
        os.path.join(submitted_directory, student_id, assignment_id, "feedback1.ipynb"),
    )

    feedback2_filename_uploaded = os.path.join(feedback_directory, student_id, assignment_id, "feedback2.html")
    copyfile(feedback2_filename, feedback2_filename_uploaded)
    copyfile(
        notebook2_filename,
        os.path.join(submitted_directory, student_id, assignment_id, "feedback2.ipynb"),
    )
    # ...... don't forget the timestamp for the submission
    with open(
        os.path.join(feedback_directory, student_id, assignment_id, "timestamp.txt"),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:01:00.0 UTC")

    # this makes the unique key & checksums for the submission
    unique_key1 = make_unique_key("no_course", assignment_id, "feedback1", student_id, "2020-01-01 00:01:00.0 UTC")
    checksum1 = notebook_hash(
        os.path.join(submitted_directory, student_id, assignment_id, "feedback1.ipynb"),
        unique_key1,
    )
    unique_key2 = make_unique_key("no_course", assignment_id, "feedback2", student_id, "2020-01-01 00:01:00.0 UTC")
    checksum2 = notebook_hash(
        os.path.join(submitted_directory, student_id, assignment_id, "feedback2.ipynb"),
        unique_key2,
    )

    plugin = ExchangeReleaseFeedback(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
    seen_feedback1 = False
    seen_feedback2 = False

    def api_request(*args, **kwargs):
        nonlocal seen_feedback1, seen_feedback2
        if "feedback1" in args[0]:
            assert seen_feedback1 is False
            seen_feedback1 = True
            assert args[0] == (
                "feedback?course_id=no_course"
                f"&assignment_id={assignment_id}"
                "&notebook=feedback1"
                f"&student={student_id}"
                "&timestamp=2020-01-01+00%3A01%3A00.0+UTC"
                "&checksum=" + checksum1
            )
            assert kwargs.get("method").lower() == "post"
            assert "feedback" in kwargs.get("files")
            assert (
                "feedback.html",
                open(feedback1_filename_uploaded).read(),
            ) == kwargs.get(
                "files"
            ).get("feedback")

        elif "feedback2" in args[0]:
            assert seen_feedback2 is False
            seen_feedback2 = True
            assert args[0] == (
                "feedback?course_id=no_course"
                f"&assignment_id={assignment_id}"
                "&notebook=feedback2"
                f"&student={student_id}"
                "&timestamp=2020-01-01+00%3A01%3A00.0+UTC"
                "&checksum=" + checksum2
            )
            assert kwargs.get("method").lower() == "post"
            assert "feedback" in kwargs.get("files")
            assert (
                "feedback.html",
                open(feedback2_filename_uploaded).read(),
            ) == kwargs.get(
                "files"
            ).get("feedback")
        else:
            assert False
        return type(
            "Request",
            (object,),
            {"status_code": 200, "json": (lambda: {"success": True})},
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        plugin.start()
        assert seen_feedback1 and seen_feedback2


@pytest.mark.gen_test
def test_release_feedback_fetch_fail(plugin_config, tmpdir):
    plugin_config.CourseDirectory.root = "/"
    plugin_config.CourseDirectory.feedback_directory = str(tmpdir.mkdir("feedback_test").realpath())
    plugin_config.CourseDirectory.submitted_directory = str(tmpdir.mkdir("submitted_test").realpath())
    plugin_config.CourseDirectory.assignment_id = assignment_id
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.feedback_directory, student_id, assignment_id),
        exist_ok=True,
    )
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.submitted_directory, student_id, assignment_id),
        exist_ok=True,
    )

    feedback_filename_uploaded = os.path.join(
        plugin_config.CourseDirectory.feedback_directory,
        student_id,
        assignment_id,
        "feedback.html",
    )
    copyfile(feedback1_filename, feedback_filename_uploaded)

    copyfile(
        notebook1_filename,
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory,
            student_id,
            assignment_id,
            "feedback.ipynb",
        ),
    )
    with open(
        os.path.join(
            plugin_config.CourseDirectory.feedback_directory,
            student_id,
            assignment_id,
            "timestamp.txt",
        ),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    plugin = ExchangeReleaseFeedback(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
            plugin.start()
        assert str(e_info.value) == "failure note"
