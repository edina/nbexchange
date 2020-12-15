import datetime
import logging
import os
import re
import shutil
import sys
from shutil import copyfile

import pytest
import requests

from mock import patch

from nbexchange.plugin import ExchangeReleaseAssignment, Exchange
from nbgrader.coursedir import CourseDirectory

from nbexchange.tests.utils import get_feedback_file
from nbgrader.exchange import ExchangeError

from nbgrader.utils import make_unique_key, notebook_hash

import nbexchange

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

course_id = "no_course"
assignment_id = "assign_1"
notebook1_filename = os.path.join(
    os.path.dirname(__file__), "data", "assignment-0.6.ipynb"
)
notebook1_file = get_feedback_file(notebook1_filename)
notebook2_filename = os.path.join(
    os.path.dirname(__file__), "data", "assignment-0.6-2.ipynb"
)
notebook2_file = get_feedback_file(notebook2_filename)


def _run_api_request(plugin, course_id, assignment_id):
    def api_request(*args, **kwargs):
        assert args[0] == (
            f"assignment?course_id={course_id}&assignment_id={assignment_id}"
        )
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
def test_release_assignment_normal(plugin_config):
    try:
        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id

        os.makedirs(
            os.path.join("release", assignment_id),
            exist_ok=True,
        )
        copyfile(
            notebook1_filename,
            os.path.join("release", assignment_id, "release.ipynb"),
        )

        plugin = ExchangeReleaseAssignment(
            coursedir=CourseDirectory(config=plugin_config), config=plugin_config
        )

        _run_api_request(plugin, course_id, assignment_id)

    finally:
        shutil.rmtree("release")


@pytest.mark.gen_test
def test_release_assignment_no_course_code(plugin_config):
    plugin_config.CourseDirectory.assignment_id = assignment_id

    plugin = ExchangeReleaseAssignment(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    with pytest.raises(
        ExchangeError, match=r"No course id specified. Re-run with --course flag."
    ):
        _run_api_request(plugin, course_id, assignment_id)


@pytest.mark.gen_test
def test_release_assignment_failure_no_files_at_all(plugin_config):
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = assignment_id

    plugin = ExchangeReleaseAssignment(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    with pytest.raises(
        ExchangeError, match=r"Assignment not found at:.*source/./assign_1"
    ):
        _run_api_request(plugin, course_id, assignment_id)


# No release is when there's no 'release/<assignment_id>', but there is a 'source/<assignment_id>'
@pytest.mark.gen_test
def test_release_assignment_failure_source_but_no_release(plugin_config):
    try:
        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id

        plugin = ExchangeReleaseAssignment(
            coursedir=CourseDirectory(config=plugin_config), config=plugin_config
        )
        os.makedirs(
            os.path.join("source", assignment_id),
            exist_ok=True,
        )
        copyfile(
            notebook1_filename,
            os.path.join("source", assignment_id, "release.ipynb"),
        )
        with pytest.raises(
            ExchangeError,
            match=r"Assignment found in \'.*/source/./assign_1\' but not \'.*/release/./assign_1\', run \`nbgrader assign\` first.",
        ):
            _run_api_request(plugin, course_id, assignment_id)
    finally:
        shutil.rmtree("source")


@pytest.mark.gen_test
def test_release_assignment_use_1_2_behaviour(plugin_config):
    # This should be no different to without the flag set
    plugin_config.use_1_2_behaviour = True
    test_release_assignment_normal(plugin_config)


@pytest.mark.gen_test
def test_release_assignment_use_course_path_everywhere(plugin_config):
    try:
        plugin_config.Exchange.use_course_path_everywhere = True

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id

        os.makedirs(
            os.path.join(course_id, "release", assignment_id),
            exist_ok=True,
        )
        copyfile(
            notebook1_filename,
            os.path.join(course_id, "release", assignment_id, "release.ipynb"),
        )

        plugin = ExchangeReleaseAssignment(
            coursedir=CourseDirectory(config=plugin_config), config=plugin_config
        )

        _run_api_request(plugin, course_id, assignment_id)

    finally:
        shutil.rmtree(course_id)


# Fuzzy is when the wrong assignment name has been given
@pytest.mark.gen_test
def test_release_assignment_use_course_path_everywhere_fuzzy(plugin_config):
    try:
        plugin_config.Exchange.use_course_path_everywhere = True

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id

        os.makedirs(
            os.path.join(course_id, "release", "other_name"),
            exist_ok=True,
        )
        copyfile(
            notebook1_filename,
            os.path.join(course_id, "release", "other_name", "release.ipynb"),
        )

        plugin = ExchangeReleaseAssignment(
            coursedir=CourseDirectory(config=plugin_config), config=plugin_config
        )

        with pytest.raises(ExchangeError, match=r"/no_course/"):
            _run_api_request(plugin, course_id, assignment_id)

    finally:
        shutil.rmtree(course_id)


# No release is when there's no 'release/<assignment_id>', but there is a 'source/<assignment_id>'
@pytest.mark.gen_test
def test_release_assignment_use_course_path_everywhere_source_but_no_release(
    plugin_config,
):
    try:
        plugin_config.Exchange.use_course_path_everywhere = True

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id

        os.makedirs(
            os.path.join(course_id, "source", assignment_id),
            exist_ok=True,
        )
        copyfile(
            notebook1_filename,
            os.path.join(course_id, "source", assignment_id, "release.ipynb"),
        )

        plugin = ExchangeReleaseAssignment(
            coursedir=CourseDirectory(config=plugin_config), config=plugin_config
        )

        with pytest.raises(
            ExchangeError,
            match=r"Assignment found in \'.*/no_course/source/./assign_1\' but not \'.*/no_course/release/./assign_1\', run \`nbgrader assign\` first.",
        ):
            _run_api_request(plugin, course_id, assignment_id)
    finally:
        shutil.rmtree(course_id)


@pytest.mark.gen_test
def test_release_assignment_ucpe_and_check_for_old_formgrader_paths_present(
    plugin_config,
):
    try:
        plugin_config.Exchange.use_course_path_everywhere = True
        plugin_config.Exchange.check_for_old_formgrader_paths = True

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id

        os.makedirs(
            os.path.join("release", assignment_id),
            exist_ok=True,
        )
        copyfile(
            notebook1_filename,
            os.path.join("release", assignment_id, "release.ipynb"),
        )

        plugin = ExchangeReleaseAssignment(
            coursedir=CourseDirectory(config=plugin_config), config=plugin_config
        )
        _run_api_request(plugin, course_id, assignment_id)

    finally:
        shutil.rmtree("release")


@pytest.mark.gen_test
def test_release_assignment_ucpe_and_check_for_old_formgrader_paths_absent(
    plugin_config,
):
    try:
        plugin_config.Exchange.use_course_path_everywhere = True
        plugin_config.Exchange.check_for_old_formgrader_paths = True

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id

        os.makedirs(
            os.path.join(course_id, "release", assignment_id),
            exist_ok=True,
        )
        copyfile(
            notebook1_filename,
            os.path.join(course_id, "release", assignment_id, "release.ipynb"),
        )

        plugin = ExchangeReleaseAssignment(
            coursedir=CourseDirectory(config=plugin_config), config=plugin_config
        )
        _run_api_request(plugin, course_id, assignment_id)

    finally:
        shutil.rmtree(course_id)


# Fuzzy is when the wrong assignment name has been given
@pytest.mark.gen_test
def test_release_assignment_ucpe_and_check_for_old_formgrader_paths_absent_fuzzy(
    plugin_config, caplog
):
    try:
        plugin_config.Exchange.use_course_path_everywhere = True
        plugin_config.Exchange.check_for_old_formgrader_paths = True

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id

        os.makedirs(
            os.path.join("source", "other_name"),
            exist_ok=True,
        )
        copyfile(
            notebook1_filename,
            os.path.join("source", "other_name", "release.ipynb"),
        )

        plugin = ExchangeReleaseAssignment(
            coursedir=CourseDirectory(config=plugin_config), config=plugin_config
        )

        with pytest.raises(ExchangeError, match=r"(?!no_course)"):
            _run_api_request(plugin, course_id, assignment_id)

    finally:
        shutil.rmtree("source")


# No release is when there's no 'release/<assignment_id>', but there is a 'source/<assignment_id>'
# Note that the 'check_for_old_formgrader_paths' trumps checking for '<course>/source/<assignment_id>'
@pytest.mark.gen_test
def test_release_assignment_ucpe_and_check_for_old_formgrader_paths_absent_no_release(
    plugin_config,
):
    try:
        plugin_config.Exchange.use_course_path_everywhere = True
        plugin_config.Exchange.check_for_old_formgrader_paths = True

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id

        os.makedirs(
            os.path.join(course_id, "source", assignment_id),
            exist_ok=True,
        )
        copyfile(
            notebook1_filename,
            os.path.join(course_id, "source", assignment_id, "release.ipynb"),
        )

        plugin = ExchangeReleaseAssignment(
            coursedir=CourseDirectory(config=plugin_config), config=plugin_config
        )

        with pytest.raises(
            ExchangeError, match=r"Assignment not found at: .*/source/./assign_1"
        ):
            _run_api_request(plugin, course_id, assignment_id)
    finally:
        shutil.rmtree(course_id)


# No release is when there's no 'release/<assignment_id>', but there is a 'source/<assignment_id>'
@pytest.mark.gen_test
def test_release_assignment_ucpe_and_check_for_old_formgrader_paths_present_no_release(
    plugin_config,
):
    try:
        plugin_config.Exchange.use_course_path_everywhere = True
        plugin_config.Exchange.check_for_old_formgrader_paths = True

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id

        os.makedirs(
            os.path.join("source", assignment_id),
            exist_ok=True,
        )
        copyfile(
            notebook1_filename,
            os.path.join("source", assignment_id, "release.ipynb"),
        )

        plugin = ExchangeReleaseAssignment(
            coursedir=CourseDirectory(config=plugin_config), config=plugin_config
        )

        with pytest.raises(
            ExchangeError,
            match=r"Assignment found in \'.*/source/./assign_1\' but not \'.*/no_course/release/./assign_1\', run \`nbgrader assign\` first.",
        ):
            _run_api_request(plugin, course_id, assignment_id)
    finally:
        shutil.rmtree("source")


@pytest.mark.gen_test
def test_release_assignment_several_normal(plugin_config):
    try:
        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id

        os.makedirs(
            os.path.join("release", assignment_id),
            exist_ok=True,
        )
        copyfile(
            notebook1_filename,
            os.path.join("release", assignment_id, "release.ipynb"),
        )
        with open(
            os.path.join("release", assignment_id, "timestamp.txt"),
            "w",
        ) as fp:
            fp.write("2020-01-01 00:00:00.0 UTC")

        copyfile(
            notebook1_filename,
            os.path.join(
                "release",
                assignment_id,
                "release1.ipynb",
            ),
        )

        copyfile(
            notebook2_filename,
            os.path.join(
                "release",
                assignment_id,
                "release2.ipynb",
            ),
        )

        plugin = ExchangeReleaseAssignment(
            coursedir=CourseDirectory(config=plugin_config), config=plugin_config
        )

        def api_request(*args, **kwargs):
            assert args[0] == (
                f"assignment?course_id=no_course" f"&assignment_id=assign_1"
            )
            assert kwargs.get("method").lower() == "post"
            assert kwargs.get("data").get("notebooks") == [
                "release",
                "release1",
                "release2",
            ]
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
    finally:
        shutil.rmtree("release")


@pytest.mark.gen_test
def test_release_assignment_several_use_course_path_everywhere(plugin_config):
    try:
        plugin_config.Exchange.use_course_path_everywhere = True

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id

        os.makedirs(
            os.path.join(course_id, "release", assignment_id),
            exist_ok=True,
        )
        copyfile(
            notebook1_filename,
            os.path.join(course_id, "release", assignment_id, "release.ipynb"),
        )
        with open(
            os.path.join(course_id, "release", assignment_id, "timestamp.txt"),
            "w",
        ) as fp:
            fp.write("2020-01-01 00:00:00.0 UTC")

        copyfile(
            notebook1_filename,
            os.path.join(
                course_id,
                "release",
                assignment_id,
                "release1.ipynb",
            ),
        )

        copyfile(
            notebook2_filename,
            os.path.join(
                course_id,
                "release",
                assignment_id,
                "release2.ipynb",
            ),
        )

        plugin = ExchangeReleaseAssignment(
            coursedir=CourseDirectory(config=plugin_config), config=plugin_config
        )

        def api_request(*args, **kwargs):
            assert args[0] == (
                f"assignment?course_id=no_course" f"&assignment_id=assign_1"
            )
            assert kwargs.get("method").lower() == "post"
            assert kwargs.get("data").get("notebooks") == [
                "release",
                "release1",
                "release2",
            ]
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
    finally:
        shutil.rmtree(course_id)


# This shows the plugin capturing an API fail
@pytest.mark.gen_test
def test_release_assignment_catches_api_fail(plugin_config, tmpdir):
    try:
        plugin_config.Exchange.use_course_path_everywhere = True

        plugin_config.CourseDirectory.course_id = course_id
        plugin_config.CourseDirectory.assignment_id = assignment_id

        os.makedirs(
            os.path.join(course_id, "release", assignment_id),
            exist_ok=True,
        )
        copyfile(
            notebook1_filename,
            os.path.join(course_id, "release", assignment_id, "release.ipynb"),
        )
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

    finally:
        shutil.rmtree(course_id)
