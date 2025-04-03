import logging
import os
import re
from shutil import copyfile

import pytest
import requests
from mock import patch
from nbgrader.coursedir import CourseDirectory
from nbgrader.exchange import ExchangeError
from tornado import web

from nbexchange.plugin import Exchange, ExchangeReleaseAssignment
from nbexchange.tests.utils import create_any_tarball, get_feedback_file

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

release_dir = "release_test"
source_dir = "source_test"
notebook1_filename = os.path.join(os.path.dirname(__file__), "data", "assignment-0.6.ipynb")
notebook1_file = get_feedback_file(notebook1_filename)
notebook2_filename = os.path.join(os.path.dirname(__file__), "data", "assignment-0.6-2.ipynb")
notebook2_file = get_feedback_file(notebook2_filename)


def test_release_assignment_methods_init_src(plugin_config, tmpdir, caplog):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.source_directory = str(tmpdir.mkdir(source_dir).realpath())
    plugin_config.CourseDirectory.release_directory = str(tmpdir.mkdir(release_dir).realpath())
    plugin_config.CourseDirectory.assignment_id = "assign_1"

    plugin = ExchangeReleaseAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    # No release file, no source file
    with pytest.raises(ExchangeError) as e_info:
        plugin.init_src()
    assert "Assignment not found at:" in str(e_info.value)

    # No release, source file exists
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.source_directory, "assign_1"),
        exist_ok=True,
    )
    copyfile(
        notebook1_filename,
        os.path.join(plugin_config.CourseDirectory.source_directory, "assign_1", "release.ipynb"),
    )
    with pytest.raises(ExchangeError) as e_info:
        plugin.init_src()
    assert re.match(
        r"Assignment found in '.+' but not '.+', run `nbgrader assign` first.",
        str(e_info.value),
    )

    # release file exists
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1"),
        exist_ok=True,
    )
    copyfile(
        notebook1_filename,
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1", "release.ipynb"),
    )
    with open(
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1", "timestamp.txt"),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")
    plugin.init_src()
    assert re.search(r"test_release_assignment_method0/release_test/./assign_1$", plugin.src_path)
    assert os.path.isdir(plugin.src_path)


@pytest.mark.gen_test
def test_release_assignment_methods_init_dest(plugin_config, tmpdir, caplog):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.release_directory = str(tmpdir.mkdir(release_dir).realpath())
    plugin_config.CourseDirectory.assignment_id = "assign_1"

    plugin = ExchangeReleaseAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
    with pytest.raises(ExchangeError) as e_info:
        plugin.init_dest()
        assert str(e_info.value) == "No course id specified. Re-run with --course flag."


@pytest.mark.gen_test
def test_release_assignment_methods_the_rest(plugin_config, tmpdir, caplog):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.release_directory = str(tmpdir.mkdir(release_dir).realpath())
    plugin_config.CourseDirectory.assignment_id = "assign_1"

    plugin = ExchangeReleaseAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1"),
        exist_ok=True,
    )
    copyfile(
        notebook1_filename,
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1", "release.ipynb"),
    )
    with open(
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1", "timestamp.txt"),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    plugin.init_src()
    with pytest.raises(AttributeError) as e_info:
        plugin.dest_path
        assert str(e_info.value) == "'ExchangeReleaseAssignment' object has no attribute 'dest_path'"

    file = plugin.tar_source()
    assert len(file) > 1000
    plugin.get_notebooks()
    assert plugin.notebooks == ["release"]


@pytest.mark.gen_test
def test_release_assignment_normal(plugin_config, tmpdir):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.release_directory = str(tmpdir.mkdir(release_dir).realpath())
    plugin_config.CourseDirectory.assignment_id = "assign_1"
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1"),
        exist_ok=True,
    )
    copyfile(
        notebook1_filename,
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1", "release.ipynb"),
    )
    with open(
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1", "timestamp.txt"),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    plugin = ExchangeReleaseAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    def api_request(*args, **kwargs):
        assert args[0] == ("assignment?course_id=no_course&assignment_id=assign_1")
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
        plugin.start()
        assert re.search(r"test_release_assignment_normal0/release_test/./assign_1$", plugin.src_path)


@pytest.mark.gen_test
def test_release_assignment_several_normal(plugin_config, tmpdir):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.release_directory = str(tmpdir.mkdir(release_dir).realpath())
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
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1", "timestamp.txt"),
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

    plugin = ExchangeReleaseAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    def api_request(*args, **kwargs):
        assert args[0] == ("assignment?course_id=no_course&assignment_id=assign_1")
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
        plugin.start()


# This has no release directory
@pytest.mark.gen_test
def test_release_assignment_missing_files(plugin_config, tmpdir, caplog):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.release_directory = str(tmpdir.mkdir(release_dir).realpath())
    plugin_config.CourseDirectory.assignment_id = "assign_1"

    plugin = ExchangeReleaseAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    with pytest.raises(ExchangeError, match="Assignment not found at:"):
        plugin.start()
    assert "Assignment not found at:" in caplog.text


@pytest.mark.gen_test
def test_release_assignment_known_failure_from_exchange(plugin_config, tmpdir):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.release_directory = str(tmpdir.mkdir(release_dir).realpath())
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
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1", "timestamp.txt"),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    plugin = ExchangeReleaseAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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


@pytest.mark.gen_test
def test_release_reducing_max_buffer_size_honoured(plugin_config, tmpdir):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.release_directory = str(tmpdir.mkdir(release_dir).realpath())
    plugin_config.CourseDirectory.assignment_id = "assign_1"
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1"),
        exist_ok=True,
    )
    copyfile(
        notebook1_filename,
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1", "release.ipynb"),
    )
    with open(
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1", "timestamp.txt"),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    plugin = ExchangeReleaseAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    # Set the max-buffer-size to 50 bytes
    plugin.max_buffer_size = 50

    def api_request(*args, **kwargs):
        assert args[0] == ("assignment?course_id=no_course&assignment_id=assign_1")
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
        with pytest.raises(ExchangeError) as e_info:
            plugin.start()
    assert "Assignment assign_1 not released." in str(e_info.value)
    assert "50B" in str(e_info.value)


@pytest.mark.gen_test
def test_release_105MB_not_blocked(plugin_config, tmpdir):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.release_directory = str(tmpdir.mkdir(release_dir).realpath())
    plugin_config.CourseDirectory.assignment_id = "assign_1"
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1"),
        exist_ok=True,
    )
    copyfile(
        notebook1_filename,
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1", "release.ipynb"),
    )
    with open(
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1", "timestamp.txt"),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    plugin = ExchangeReleaseAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    def api_request(*args, **kwargs):
        assert args[0] == ("assignment?course_id=no_course&assignment_id=assign_1")
        assert kwargs.get("method").lower() == "post"
        assert kwargs.get("data").get("notebooks") == ["release"]
        assert "assignment" in kwargs.get("files")
        assert "assignment.tar.gz" == kwargs.get("files").get("assignment")[0]

        return type(
            "Request",
            (object,),
            {"status_code": 200, "json": (lambda: {"success": True})},
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        with patch.object(ExchangeReleaseAssignment, "tar_source", return_value=create_any_tarball(110100480)):  # 105MB
            plugin.start()
    assert True  # No failure


# @pytest.mark.gen_test
def test_release_5point1GB_is_blocked__long_test(plugin_config, tmpdir):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.release_directory = str(tmpdir.mkdir(release_dir).realpath())
    plugin_config.CourseDirectory.assignment_id = "assign_1"
    os.makedirs(
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1"),
        exist_ok=True,
    )

    plugin = ExchangeReleaseAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    def api_request(*args, **kwargs):
        raise web.HTTPError(status_code=400, log_message="Bad Request")

    with patch.object(Exchange, "api_request", side_effect=api_request):
        with patch.object(
            ExchangeReleaseAssignment, "tar_source", return_value=create_any_tarball(5476083302)  # 5.1GB
        ):
            with pytest.raises(ExchangeError) as e_info:
                plugin.start()
            assert "Assignment assign_1 not released." in str(e_info.value)
            assert "4.9G" in str(e_info.value)


@pytest.mark.gen_test
def test_release_does_timeout(plugin_config, tmpdir, caplog):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.release_directory = str(tmpdir.mkdir(release_dir).realpath())
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
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1", "timestamp.txt"),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    plugin = ExchangeReleaseAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    def api_request(*args, **kwargs):
        raise requests.exceptions.Timeout

    expected_message = "Timed out trying to reach the exchange service to release assignment."
    with patch.object(Exchange, "api_request", side_effect=api_request):
        with pytest.raises(ExchangeError, match=expected_message):
            plugin.start()
    assert expected_message in caplog.text


@pytest.mark.gen_test
def test_release_assignment_exchange_failure_code(plugin_config, tmpdir, caplog):
    plugin_config.CourseDirectory.root = "/"

    plugin_config.CourseDirectory.release_directory = str(tmpdir.mkdir(release_dir).realpath())
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
        os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1", "timestamp.txt"),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    plugin = ExchangeReleaseAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    def api_request(*args, **kwargs):
        raise web.HTTPError(status_code=418, log_message="Use leaves, not bags")

    with patch.object(Exchange, "api_request", side_effect=api_request):
        with pytest.raises(Exception) as e_info:
            plugin.start()
        assert e_info.type is web.HTTPError
        assert str(e_info.value) == "HTTP 418: I'm a Teapot (Use leaves, not bags)"
