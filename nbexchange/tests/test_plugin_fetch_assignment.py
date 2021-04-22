import io
import logging
import os
import shutil
import tarfile
from shutil import copyfile

import pytest
from mock import patch
from nbgrader.coursedir import CourseDirectory

from nbexchange.plugin import Exchange, ExchangeFetchAssignment
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
def test_fetch_assignment_fetch_normal(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = "assign_1_2"

    plugin = ExchangeFetchAssignment(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    try:

        def api_request(*args, **kwargs):
            tar_file = io.BytesIO()

            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(
                    notebook1_filename, arcname=os.path.basename(notebook1_filename)
                )
            tar_file.seek(0)

            assert args[0] == (
                f"assignment?course_id=no_course&assignment_id=assign_1_2"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "content": tar_file.read(),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            assert os.path.exists(
                os.path.join(plugin.dest_path, "assignment-0.6.ipynb")
            )
    finally:
        shutil.rmtree(plugin.dest_path)


@pytest.mark.gen_test
def test_fetch_assignment_fetch_normal_with_path_includes_course(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = "assign_1_2"
    plugin_config.Exchange.path_includes_course = True

    plugin = ExchangeFetchAssignment(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    try:

        def api_request(*args, **kwargs):
            tar_file = io.BytesIO()

            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(
                    notebook1_filename, arcname=os.path.basename(notebook1_filename)
                )
            tar_file.seek(0)

            assert args[0] == (
                f"assignment?course_id=no_course&assignment_id=assign_1_2"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "content": tar_file.read(),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            assert os.path.exists(
                os.path.join(plugin.dest_path, "assignment-0.6.ipynb")
            )
    finally:
        shutil.rmtree(plugin.dest_path)


@pytest.mark.gen_test
def test_fetch_assignment_fetch_several_normal(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = "assign_1_3"

    plugin = ExchangeFetchAssignment(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )
    try:

        def api_request(*args, **kwargs):
            tar_file = io.BytesIO()

            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(
                    notebook1_filename, arcname=os.path.basename(notebook1_filename)
                )
                tar_handle.add(
                    notebook2_filename, arcname=os.path.basename(notebook2_filename)
                )
            tar_file.seek(0)

            assert args[0] == (
                f"assignment?course_id=no_course&assignment_id=assign_1_3"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "content": tar_file.read(),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            assert os.path.exists(
                os.path.join(plugin.dest_path, "assignment-0.6.ipynb")
            )
            assert os.path.exists(
                os.path.join(plugin.dest_path, "assignment-0.6-2.ipynb")
            )
    finally:
        shutil.rmtree(plugin.dest_path)
