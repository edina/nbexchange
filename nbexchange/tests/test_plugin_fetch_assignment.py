import io
import logging
import os
import re
import shutil
import tarfile
import urllib.parse
from shutil import copyfile

import pytest
from mock import patch
from nbgrader.coursedir import CourseDirectory
from nbgrader.exchange import ExchangeError

from nbexchange.plugin import Exchange, ExchangeFetchAssignment
from nbexchange.tests.utils import get_feedback_file

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


notebook1_filename = os.path.join(os.path.dirname(__file__), "data", "assignment-0.6.ipynb")
notebook1_file = get_feedback_file(notebook1_filename)
notebook2_filename = os.path.join(os.path.dirname(__file__), "data", "assignment-0.6-2.ipynb")
notebook2_file = get_feedback_file(notebook2_filename)

course_id = "no_course"
ass_1_2 = "assign_1_2"
ass_1_3 = "assign_1_3"
ass_1_a2ovi = "⍺ to ⍵ via ∞"


@pytest.mark.gen_test
def test_fetch_assignment_methods_init_dest(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = ass_1_2

    plugin = ExchangeFetchAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    # we're good if the dir doesn't exist
    plugin.init_dest()
    assert re.search(rf"{ass_1_2}$", plugin.dest_path)
    assert os.path.isdir(plugin.dest_path)

    # we're good if the dir exists and is empty
    plugin.init_dest()
    assert re.search(rf"{ass_1_2}$", plugin.dest_path)

    # we're good if the dir exists, and has something OTHER than an ipynb file in it
    with open(f"{plugin.dest_path}/random.txt", "w") as fp:
        fp.write("Hello world")
    plugin.init_dest()
    assert re.search(rf"{ass_1_2}$", plugin.dest_path)

    # FAILS if the dir exists AND there's an ipynb file in it
    with open(f"{plugin.dest_path}/random.ipynb", "w") as fp:
        fp.write("Hello world")
    with pytest.raises(ExchangeError) as e_info:
        plugin.init_dest()
    assert (
        f"You already have notebook documents in directory: {plugin_config.CourseDirectory.assignment_id}. Please remove them before fetching again"
        in str(e_info.value)
    )
    shutil.rmtree(plugin.dest_path)


@pytest.mark.gen_test
def test_fetch_assignment_methods_rest(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = ass_1_2

    plugin = ExchangeFetchAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    plugin.init_src()
    assert re.search(rf"{course_id}/{ass_1_2}/assignment.tar.gz$", plugin.src_path)
    plugin.init_dest()

    try:

        def api_request(*args, **kwargs):
            tar_file = io.BytesIO()

            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(notebook1_filename, arcname=os.path.basename(notebook1_filename))
            tar_file.seek(0)

            assert args[0] == (f"assignment?course_id={course_id}&assignment_id={ass_1_2}")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/gzip"},
                    "content": tar_file.read(),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            plugin.download()
            assert os.path.exists(os.path.join(plugin.src_path, "assignment-0.6.ipynb"))
            shutil.rmtree(plugin.dest_path)

            # do_copy includes a download()
            plugin.do_copy(plugin.src_path, plugin.dest_path)
            assert os.path.exists(os.path.join(plugin.dest_path, "assignment-0.6.ipynb"))
    finally:
        shutil.rmtree(plugin.dest_path)


@pytest.mark.gen_test
def test_fetch_assignment_fetch_normal(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = ass_1_2

    plugin = ExchangeFetchAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    try:

        def api_request(*args, **kwargs):
            tar_file = io.BytesIO()

            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(notebook1_filename, arcname=os.path.basename(notebook1_filename))
            tar_file.seek(0)

            assert args[0] == (f"assignment?course_id={course_id}&assignment_id={ass_1_2}")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/gzip"},
                    "content": tar_file.read(),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            plugin.start()
            assert os.path.exists(os.path.join(plugin.dest_path, "assignment-0.6.ipynb"))
    finally:
        shutil.rmtree(plugin.dest_path)


@pytest.mark.gen_test
def test_fetch_assignment_fetch_normal_with_path_includes_course(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = ass_1_2
    plugin_config.Exchange.path_includes_course = True

    plugin = ExchangeFetchAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    try:

        def api_request(*args, **kwargs):
            tar_file = io.BytesIO()

            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(notebook1_filename, arcname=os.path.basename(notebook1_filename))
            tar_file.seek(0)

            assert args[0] == (f"assignment?course_id={course_id}&assignment_id={ass_1_2}")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/gzip"},
                    "content": tar_file.read(),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            plugin.start()
            assert os.path.exists(os.path.join(plugin.dest_path, "assignment-0.6.ipynb"))
    finally:
        shutil.rmtree(plugin.dest_path)


@pytest.mark.gen_test
def test_fetch_assignment_fetch_several_normal(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = ass_1_3

    plugin = ExchangeFetchAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
    try:

        def api_request(*args, **kwargs):
            tar_file = io.BytesIO()

            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(notebook1_filename, arcname=os.path.basename(notebook1_filename))
                tar_handle.add(notebook2_filename, arcname=os.path.basename(notebook2_filename))
            tar_file.seek(0)

            assert args[0] == (f"assignment?course_id={course_id}&assignment_id=assign_1_3")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/gzip"},
                    "content": tar_file.read(),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            plugin.start()
            assert os.path.exists(os.path.join(plugin.dest_path, "assignment-0.6.ipynb"))
            assert os.path.exists(os.path.join(plugin.dest_path, "assignment-0.6-2.ipynb"))
    finally:
        shutil.rmtree(plugin.dest_path)


@pytest.mark.gen_test
def test_fetch_empty_folder_exists(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = ass_1_3

    plugin = ExchangeFetchAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
    os.makedirs(ass_1_3)
    try:

        def api_request(*args, **kwargs):
            tar_file = io.BytesIO()

            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(notebook1_filename, arcname=os.path.basename(notebook1_filename))
                tar_handle.add(notebook2_filename, arcname=os.path.basename(notebook2_filename))
            tar_file.seek(0)

            assert args[0] == (f"assignment?course_id={course_id}&assignment_id=assign_1_3")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/gzip"},
                    "content": tar_file.read(),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            plugin.start()
            assert os.path.exists(os.path.join(plugin.dest_path, "assignment-0.6.ipynb"))
            assert os.path.exists(os.path.join(plugin.dest_path, "assignment-0.6-2.ipynb"))
    finally:
        shutil.rmtree(plugin.dest_path)


@pytest.mark.gen_test
def test_fetch_folder_exists_with_ipynb(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = ass_1_3

    plugin = ExchangeFetchAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
    os.makedirs(ass_1_3)
    with open("assign_1_3/decoy.ipynb", "w") as f:
        f.write(" ")
    try:

        def api_request(*args, **kwargs):
            tar_file = io.BytesIO()

            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(notebook1_filename, arcname=os.path.basename(notebook1_filename))
                tar_handle.add(notebook2_filename, arcname=os.path.basename(notebook2_filename))
            tar_file.seek(0)

            assert args[0] == (f"assignment?course_id={course_id}&assignment_id=assign_1_3")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/gzip"},
                    "content": tar_file.read(),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            with pytest.raises(ExchangeError) as e_info:
                plugin.start()
            assert (
                str(e_info.value)
                == "You already have notebook documents in directory: assign_1_3. Please remove them before fetching again"
            )
    finally:
        shutil.rmtree(plugin.dest_path)


@pytest.mark.gen_test
def test_fetch_folder_exists_with_other_file(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = ass_1_3

    plugin = ExchangeFetchAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
    os.makedirs(ass_1_3)
    with open("assign_1_3/decoy.txt", "w") as f:
        f.write(" ")
    try:

        def api_request(*args, **kwargs):
            tar_file = io.BytesIO()

            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(notebook1_filename, arcname=os.path.basename(notebook1_filename))
                tar_handle.add(notebook2_filename, arcname=os.path.basename(notebook2_filename))
            tar_file.seek(0)

            assert args[0] == (f"assignment?course_id={course_id}&assignment_id=assign_1_3")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/gzip"},
                    "content": tar_file.read(),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            plugin.start()
            assert os.path.exists(os.path.join(plugin.dest_path, "assignment-0.6.ipynb"))
            assert os.path.exists(os.path.join(plugin.dest_path, "assignment-0.6-2.ipynb"))
    finally:
        shutil.rmtree(plugin.dest_path)


@pytest.mark.gen_test
def test_fetch_assignment_handles_500_failure(plugin_config):
    http_error = "blown op"
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = ass_1_2

    plugin = ExchangeFetchAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
    try:

        def api_request(*args, **kwargs):
            return type(
                "Response",
                (object,),
                {
                    "status_code": 500,
                    "headers": {"content-type": "application/gzip"},
                    "content": http_error,
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            with pytest.raises(ExchangeError) as e_info:
                plugin.start()
            assert (
                str(e_info.value)
                == f"Error failing to fetch assignment {ass_1_2} on course {course_id}: status code 500: error {http_error}"
            )
    finally:
        shutil.rmtree(plugin.dest_path)


@pytest.mark.gen_test
def test_fetch_assignment_fetch_unicode(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = course_id
    plugin_config.CourseDirectory.assignment_id = ass_1_a2ovi

    plugin = ExchangeFetchAssignment(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    try:

        def api_request(*args, **kwargs):
            tar_file = io.BytesIO()

            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(notebook1_filename, arcname=os.path.basename(notebook1_filename))
            tar_file.seek(0)

            assert args[0] == (f"assignment?course_id={course_id}&assignment_id={urllib.parse.quote_plus(ass_1_a2ovi)}")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/gzip"},
                    "content": tar_file.read(),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            plugin.start()
            assert os.path.basename(plugin.dest_path) == ass_1_a2ovi
            assert os.path.exists(os.path.join(plugin.dest_path, "assignment-0.6.ipynb"))
    finally:
        shutil.rmtree(plugin.dest_path)
