import io
import logging
import os
import re
import shutil
import tarfile
from os.path import basename
from shutil import copyfile

import pytest
from mock import patch
from nbgrader.coursedir import CourseDirectory
from nbgrader.exchange import ExchangeError

from nbexchange.plugin import Exchange, ExchangeSubmit
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

course_id = "no_course"
assignment_id1 = "assign_1_1"
assignment_id2 = "assign_1_2"
assignment_id3 = "assign_1_3"


@pytest.mark.gen_test
def test_submit_methods(plugin_config, tmpdir, caplog):
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = assignment_id1

    os.makedirs(assignment_id1, exist_ok=True)
    copyfile(
        notebook1_filename,
        os.path.join(assignment_id1, basename(notebook1_filename)),
    )

    plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
    plugin.init_src()
    assert re.search(r"nbexchange/assign_1_1$", plugin.src_path)
    plugin.init_dest()
    with pytest.raises(AttributeError) as e_info:
        plugin.dest_path
        assert str(e_info.value) == "'ExchangeReleaseAssignment' object has no attribute 'dest_path'"
    file = plugin.tar_source()
    assert len(file) > 1000

    def api_request_wrong_nb(*args, **kwargs):
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
                                "assignment_id": assignment_id1,
                                "student_id": "1",
                                "course_id": course_id,
                                "status": "released",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": "assignment-0.6.1",
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

    def api_request_right_nb(*args, **kwargs):
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
                                "assignment_id": assignment_id1,
                                "student_id": "1",
                                "course_id": course_id,
                                "status": "released",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": "assignment-0.6",
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

    with patch.object(Exchange, "api_request", side_effect=api_request_wrong_nb):
        plugin.check_filename_diff()
        assert "assignment-0.6.1.ipynb: MISSING" in caplog.text
        assert "assignment-0.6.ipynb: EXTRA" in caplog.text
    caplog.clear()  # clears the capture from above
    with patch.object(Exchange, "api_request", side_effect=api_request_right_nb):
        plugin.check_filename_diff()
        assert caplog.text == ""


# Straight simple submission works
@pytest.mark.gen_test
def test_submit_single_item(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id1

        os.makedirs(assignment_id1, exist_ok=True)
        copyfile(
            notebook1_filename,
            os.path.join(assignment_id1, basename(notebook1_filename)),
        )

        plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                        "assignment_id": assignment_id1,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
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
                assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id1}")
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
            plugin.start()
    finally:
        shutil.rmtree(assignment_id1)


# Confirm submit knows to look for path_includes_course
@pytest.mark.gen_test
def test_submit_single_item_with_path_includes_course(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id1
        plugin_config.Exchange.path_includes_course = True

        os.makedirs(os.path.join(course_id, assignment_id1), exist_ok=True)
        copyfile(
            notebook1_filename,
            os.path.join(course_id, assignment_id1, basename(notebook1_filename)),
        )

        plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                        "assignment_id": assignment_id1,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
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
                assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id1}")
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
            plugin.start()
    finally:
        shutil.rmtree(os.path.join(course_id, assignment_id1))


# What does this *DO*?
@pytest.mark.gen_test
def test_submit_fail(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id1

        os.makedirs(assignment_id1, exist_ok=True)
        copyfile(
            notebook1_filename,
            os.path.join(assignment_id1, basename(notebook1_filename)),
        )

        plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                        "assignment_id": assignment_id1,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
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
                assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id1}")
                assert "method" not in kwargs or kwargs.get("method").lower() == "post"

                return type(
                    "Request",
                    (object,),
                    {
                        "status_code": 200,
                        "json": (lambda: {"success": False, "note": "failure note"}),
                    },
                )

        with pytest.raises(ExchangeError) as e_info, patch.object(Exchange, "api_request", side_effect=api_request):
            plugin.start()
        assert str(e_info.value) == "failure note"
    finally:
        shutil.rmtree(assignment_id1)


# Submission can have multiple notebooks
@pytest.mark.gen_test
def test_submit_multiple_notebooks_in_assignment(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = assignment_id3

    os.makedirs(assignment_id3, exist_ok=True)
    copyfile(notebook1_filename, os.path.join(assignment_id3, basename(notebook1_filename)))
    copyfile(notebook2_filename, os.path.join(assignment_id3, basename(notebook2_filename)))

    plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
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
                                        "assignment_id": assignment_id3,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": False,
                                            },
                                            {
                                                "notebook_id": "assignment-0.6-2",
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
                assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id3}")
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
            plugin.start()
    finally:
        shutil.rmtree(assignment_id3)


# Failure, no assignment folder found when submitting
# Note the execption is raised around the "start()"
@pytest.mark.gen_test
def test_submit_fail_no_folder(plugin_config, tmpdir):
    try:
        plugin_config.strict = False

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id1

        plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                        "assignment_id": assignment_id1,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
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
                assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id1}")
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

        with pytest.raises(ExchangeError, match=r"Assignment not found at"):
            with patch.object(Exchange, "api_request", side_effect=api_request):
                plugin.start()
    finally:
        pass  # shutil.rmtree(assignment_id1)


# Failure: assignment folder exists, but no files when submitting
@pytest.mark.gen_test
def test_submit_warning_no_notebook(plugin_config, tmpdir):
    try:

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id1

        os.makedirs(assignment_id1, exist_ok=True)

        plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                        "assignment_id": assignment_id1,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
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
                with pytest.warns(
                    UserWarning,
                    match=r"Possible missing notebooks and/or extra notebooks",
                ):
                    pth = str(tmpdir.mkdir("submit_several").realpath())
                    assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id1}")
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
                plugin.start()

    finally:
        shutil.rmtree(assignment_id1)


# Failure: assignment folder exists, but wrong files
@pytest.mark.gen_test
def test_submit_warning_wrong_notebook(plugin_config, tmpdir):
    try:

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id1

        os.makedirs(assignment_id1, exist_ok=True)
        copyfile(
            notebook2_filename,
            os.path.join(assignment_id1, basename(notebook1_filename)),
        )

        plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                        "assignment_id": assignment_id1,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
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
                with pytest.warns(
                    UserWarning,
                    match=r"Possible missing notebooks and/or extra notebooks",
                ):
                    pth = str(tmpdir.mkdir("submit_several").realpath())
                    assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id1}")
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
                plugin.start()

    finally:
        shutil.rmtree(assignment_id1)


# Failure: assignment folder exists, wrong files - and "strict" is true
# Raises error.
@pytest.mark.gen_test
def test_submit_no_notebook_strict_means_fail(plugin_config, tmpdir):
    try:
        plugin_config.strict = True

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id1

        os.makedirs(assignment_id1, exist_ok=True)

        plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                        "assignment_id": assignment_id1,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
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
                with pytest.raises(ExchangeError, match=r"Assignment \w+ not submitted"):
                    pth = str(tmpdir.mkdir("submit_several").realpath())
                    assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id1}")
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
                plugin.start()

    finally:
        shutil.rmtree(assignment_id1)


# Failure: assignment folder exists, but wrong files
@pytest.mark.gen_test
def test_submit_wrong_notebook_strict_means_faile(plugin_config, tmpdir):
    try:
        plugin_config.strict = True

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id1

        os.makedirs(assignment_id1, exist_ok=True)
        copyfile(
            notebook2_filename,
            os.path.join(assignment_id1, basename(notebook1_filename)),
        )

        plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                        "assignment_id": assignment_id1,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
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
                with pytest.raises(ExchangeError, match=r"Assignment \w+ not submitted"):
                    pth = str(tmpdir.mkdir("submit_several").realpath())
                    assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id1}")
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
                plugin.start()

    finally:
        shutil.rmtree(assignment_id1)


# Failure: assignment folder exists, but extra files
@pytest.mark.gen_test
def test_submit_warning_wrong_notebook_two(plugin_config, tmpdir):
    try:

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id1

        os.makedirs(assignment_id1, exist_ok=True)
        copyfile(
            notebook1_filename,
            os.path.join(assignment_id1, basename(notebook1_filename)),
        )
        copyfile(
            notebook2_filename,
            os.path.join(assignment_id1, basename(notebook2_filename)),
        )
        plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                        "assignment_id": assignment_id1,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
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
                with pytest.warns(
                    UserWarning,
                    match=r"Possible missing notebooks and/or extra notebooks",
                ):
                    pth = str(tmpdir.mkdir("submit_several").realpath())
                    assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id1}")
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
                plugin.start()

    finally:
        shutil.rmtree(assignment_id1)


# Failure: assignment folder exists, but wrong files
@pytest.mark.gen_test
def test_submit_extra_notebook_strict_means_fail(plugin_config, tmpdir):
    try:
        plugin_config.strict = True

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id1

        os.makedirs(assignment_id1, exist_ok=True)
        copyfile(
            notebook2_filename,
            os.path.join(assignment_id1, basename(notebook1_filename)),
        )

        plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                        "assignment_id": assignment_id1,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
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
                with pytest.raises(ExchangeError, match=r"Assignment \w+ not submitted"):
                    pth = str(tmpdir.mkdir("submit_several").realpath())
                    assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id1}")
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
                plugin.start()

    finally:
        shutil.rmtree(assignment_id1)


# Check we use the right "release" details, variant 1 of 3
@pytest.mark.gen_test
def test_submit_two_releases_newest_first(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id1

        os.makedirs(assignment_id1, exist_ok=True)
        copyfile(
            notebook1_filename,
            os.path.join(assignment_id1, basename(notebook1_filename)),
        )

        plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                        "assignment_id": assignment_id2,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6-2",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": False,
                                            }
                                        ],
                                        "timestamp": "2020-01-01 00:01:00.0 UTC",
                                    },
                                    {
                                        "assignment_id": assignment_id1,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": False,
                                            }
                                        ],
                                        "timestamp": "2020-01-01 00:00:00.0 UTC",
                                    },
                                ],
                            }
                        ),
                    },
                )
            else:
                pth = str(tmpdir.mkdir("submit_several").realpath())
                assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id1}")
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
            plugin.start()
    finally:
        shutil.rmtree(assignment_id1)


# Check we use the right "release" details, variant 2 of 3
@pytest.mark.gen_test
def test_submit_two_releases_newest_last(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id1

        os.makedirs(assignment_id1, exist_ok=True)
        copyfile(
            notebook1_filename,
            os.path.join(assignment_id1, basename(notebook1_filename)),
        )

        plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                        "assignment_id": assignment_id2,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6-2",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": False,
                                            }
                                        ],
                                        "timestamp": "2020-01-01 00:00:00.0 UTC",
                                    },
                                    {
                                        "assignment_id": assignment_id1,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": False,
                                            }
                                        ],
                                        "timestamp": "2020-01-01 00:01:00.0 UTC",
                                    },
                                ],
                            }
                        ),
                    },
                )
            else:
                pth = str(tmpdir.mkdir("submit_several").realpath())
                assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id1}")
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
            plugin.start()
    finally:
        shutil.rmtree(assignment_id1)


# Failure: assignment folder exists, but wrong files
@pytest.mark.gen_test
def test_submit_warning_wrong_notebook_three(plugin_config, tmpdir):
    try:

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id1

        os.makedirs(assignment_id1, exist_ok=True)
        copyfile(
            notebook2_filename,
            os.path.join(assignment_id1, basename(notebook1_filename)),
        )

        plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                        "assignment_id": assignment_id2,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": False,
                                            }
                                        ],
                                        "timestamp": "2020-01-01 00:00:00.0 UTC",
                                    },
                                    {
                                        "assignment_id": assignment_id1,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": False,
                                            }
                                        ],
                                        "timestamp": "2020-01-01 00:01:00.0 UTC",
                                    },
                                ],
                            }
                        ),
                    },
                )
            else:
                with pytest.warns(
                    UserWarning,
                    match=r"Possible missing notebooks and/or extra notebooks",
                ):
                    pth = str(tmpdir.mkdir("submit_several").realpath())
                    assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id1}")
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
                plugin.start()

    finally:
        shutil.rmtree(assignment_id1)


# What happens when we have multiple assignments in the list
@pytest.mark.gen_test
def test_submit_with_multiple_assignments_newest_first(plugin_config, tmpdir):
    pass
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = assignment_id3

    os.makedirs(assignment_id3, exist_ok=True)
    copyfile(notebook1_filename, os.path.join(assignment_id3, basename(notebook1_filename)))

    plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
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
                                        "assignment_id": assignment_id3,
                                        "student_id": 1,
                                        "course_id": course_id,
                                        "status": "fetched",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            }
                                        ],
                                        "timestamp": "2020-03-02 11:58:27.5 00:00",
                                    },
                                    {
                                        "assignment_id": assignment_id3,
                                        "student_id": 1,
                                        "course_id": course_id,
                                        "status": "submitted",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            }
                                        ],
                                        "timestamp": "2020-03-02 08:26:01.4 00:00",
                                    },
                                    {
                                        "assignment_id": assignment_id3,
                                        "student_id": 1,
                                        "course_id": course_id,
                                        "status": "fetched",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            }
                                        ],
                                        "timestamp": "2020-03-02 08:07:28.61 00:00",
                                    },
                                    {
                                        "assignment_id": assignment_id3,
                                        "student_id": 1,
                                        "course_id": course_id,
                                        "status": "submitted",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            }
                                        ],
                                        "timestamp": "2020-03-02 07:20:37.7 00:00",
                                    },
                                    {
                                        "assignment_id": assignment_id3,
                                        "student_id": 1,
                                        "course_id": course_id,
                                        "status": "fetched",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            }
                                        ],
                                        "timestamp": "2020-03-02 07:20:32.3 00:00",
                                    },
                                    {
                                        "assignment_id": assignment_id3,
                                        "student_id": 2,
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            }
                                        ],
                                        "timestamp": "2020-03-01 12:56:44.6 00:00",
                                    },
                                    {
                                        "assignment_id": "assign_1_3",
                                        "student_id": 2,
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.5",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            },
                                        ],
                                        "timestamp": "2020-03-01 10:45:49.9 00:00",
                                    },
                                    {
                                        "assignment_id": assignment_id1,
                                        "student_id": 2,
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "1 - Introduction to the IPython notebook",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            },
                                            {
                                                "notebook_id": "2 - Markdown and LaTeX Cheatsheet",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            },
                                            {
                                                "notebook_id": "3 - Introduction to NumPy",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            },
                                            {
                                                "notebook_id": "For reference - Debugging",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            },
                                            {
                                                "notebook_id": "For reference - Python recap",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            },
                                        ],
                                        "timestamp": "2020-01-01 10:45:49.9 00:00",
                                    },
                                ],
                            }
                        ),
                    },
                )
            else:
                pth = str(tmpdir.mkdir("submit_several").realpath())
                assert args[0] == (f"submission?course_id={course_id}&assignment_id=assign_1_3")
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
            plugin.start()
    finally:
        shutil.rmtree(assignment_id3)


# What happens when we have multiple assignments in the list
@pytest.mark.gen_test
def test_submit_with_multiple_assignments_oldest_first(plugin_config, tmpdir):
    pass
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = assignment_id3

    os.makedirs(assignment_id3, exist_ok=True)
    copyfile(notebook1_filename, os.path.join(assignment_id3, basename(notebook1_filename)))

    plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
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
                                        "assignment_id": assignment_id1,
                                        "student_id": 2,
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "1 - Introduction to the IPython notebook",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            },
                                            {
                                                "notebook_id": "2 - Markdown and LaTeX Cheatsheet",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            },
                                            {
                                                "notebook_id": "3 - Introduction to NumPy",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            },
                                            {
                                                "notebook_id": "For reference - Debugging",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            },
                                            {
                                                "notebook_id": "For reference - Python recap",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            },
                                        ],
                                        "timestamp": "2020-01-01 10:45:49.9 00:00",
                                    },
                                    {
                                        "assignment_id": assignment_id3,
                                        "student_id": 1,
                                        "course_id": course_id,
                                        "status": "fetched",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            }
                                        ],
                                        "timestamp": "2020-03-02 11:58:27.5 00:00",
                                    },
                                    {
                                        "assignment_id": assignment_id3,
                                        "student_id": 1,
                                        "course_id": course_id,
                                        "status": "submitted",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            }
                                        ],
                                        "timestamp": "2020-03-02 08:26:01.4 00:00",
                                    },
                                    {
                                        "assignment_id": assignment_id3,
                                        "student_id": 1,
                                        "course_id": course_id,
                                        "status": "fetched",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            }
                                        ],
                                        "timestamp": "2020-03-02 08:07:28.61 00:00",
                                    },
                                    {
                                        "assignment_id": assignment_id3,
                                        "student_id": 1,
                                        "course_id": course_id,
                                        "status": "submitted",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            }
                                        ],
                                        "timestamp": "2020-03-02 07:20:37.7 00:00",
                                    },
                                    {
                                        "assignment_id": assignment_id3,
                                        "student_id": 1,
                                        "course_id": course_id,
                                        "status": "fetched",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            }
                                        ],
                                        "timestamp": "2020-03-02 07:20:32.3 00:00",
                                    },
                                    {
                                        "assignment_id": assignment_id3,
                                        "student_id": 2,
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            }
                                        ],
                                        "timestamp": "2020-03-01 12:56:44.6 00:00",
                                    },
                                    {
                                        "assignment_id": "assign_1_3",
                                        "student_id": 2,
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.5",
                                                "has_exchange_feedback": False,
                                                "feedback_updated": False,
                                                "feedback_timestamp": None,
                                            },
                                        ],
                                        "timestamp": "2020-03-01 10:45:49.9 00:00",
                                    },
                                ],
                            }
                        ),
                    },
                )
            else:
                pth = str(tmpdir.mkdir("submit_several").realpath())
                assert args[0] == (f"submission?course_id={course_id}&assignment_id=assign_1_3")
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
            plugin.start()
    finally:
        shutil.rmtree(assignment_id3)


# Check the client-side oversizxe limit works
@pytest.mark.gen_test
def test_submit_fails_oversize(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id1

        os.makedirs(assignment_id1, exist_ok=True)
        copyfile(
            notebook1_filename,
            os.path.join(assignment_id1, basename(notebook1_filename)),
        )

        plugin = ExchangeSubmit(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

        # Set the max-buffer-size to 50 bytes
        plugin.max_buffer_size = 50

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
                                        "assignment_id": assignment_id1,
                                        "student_id": "1",
                                        "course_id": course_id,
                                        "status": "released",
                                        "path": "",
                                        "notebooks": [
                                            {
                                                "notebook_id": "assignment-0.6",
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
                assert args[0] == (f"submission?course_id={course_id}&assignment_id={assignment_id1}")
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
            with pytest.raises(ExchangeError) as e_info:
                plugin.start()
            assert (
                str(e_info.value)
                == "Assignment assign_1_1 not submitted. The contents of your submission are too large:\nYou may have data files, temporary files, and/or working files that are not needed - try deleting them."  # noqa E501
            )

    finally:
        shutil.rmtree(assignment_id1)
