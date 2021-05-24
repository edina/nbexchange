import io
import logging
import os
import shutil
import tarfile
from shutil import copyfile

import pytest
from mock import patch
from nbgrader.api import Gradebook
from nbgrader.coursedir import CourseDirectory

from nbexchange.plugin import Exchange, ExchangeCollect
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

student_id = "1"
ass_1_1 = "assign_1_1"
ass_1_2 = "assign_1_2"
ass_1_3 = "assign_1_3"
ass_1_4 = "assign_1_4"
ass_1_5 = "assign_1_5"


@pytest.mark.gen_test
def test_collect_methods(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = ass_1_3
    plugin_config.CourseDirectory.submitted_directory = str(
        tmpdir.mkdir("submitted").realpath()
    )
    plugin = ExchangeCollect(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    plugin.init_src()
    with pytest.raises(AttributeError) as e_info:
        foo = plugin.src_path
        assert (
            str(e_info.value) == "'ExchangeCollect' object has no attribute 'src_path'"
        )
    plugin.init_dest()
    with pytest.raises(AttributeError) as e_info:
        foo = plugin.dest_path
        assert (
            str(e_info.value) == "'ExchangeCollect' object has no attribute 'dest_path'"
        )

    def api_request_good(*args, **kwargs):
        tar_file = io.BytesIO()

        assert "method" not in kwargs or kwargs.get("method").lower() == "get"
        with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
            tar_handle.add(
                notebook1_filename, arcname=os.path.basename(notebook1_filename)
            )
            # tar_handle.add(notebook2_filename, arcname=os.path.basename(notebook2_filename))
        tar_file.seek(0)

        return type(
            "Response",
            (object,),
            {
                "status_code": 200,
                "headers": {"content-type": "application/x-tar"},
                "content": tar_file.read(),
            },
        )

    def api_request_bad(*args, **kwargs):
        return type(
            "Response",
            (object,),
            {
                "status_code": 200,
                "headers": {"content-type": "application/x-tar"},
                "content": b"",
            },
        )

    with patch.object(Exchange, "api_request", side_effect=api_request_bad):
        submission = {
            "student_id": student_id,
            "path": f"/submitted/no_course/{ass_1_3}/1/",
            "timestamp": "2020-01-01 00:00:00.0 UTC",
        }
        dest_path = f"{plugin_config.CourseDirectory.submitted_directory}/123/{ass_1_3}"
        with pytest.raises(Exception) as e_info:
            plugin.download(submission, dest_path)
        assert str(e_info.value) == "file could not be opened successfully"


@pytest.mark.gen_test
def test_collect_normal(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = ass_1_3
    plugin_config.CourseDirectory.submitted_directory = str(
        tmpdir.mkdir("submitted").realpath()
    )
    plugin = ExchangeCollect(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )
    collections = False
    collection = False

    def api_request(*args, **kwargs):
        nonlocal collections, collection
        tar_file = io.BytesIO()
        if "collections" in args[0]:
            assert collections is False
            collections = True
            assert args[0] == (
                f"collections?course_id=no_course&assignment_id={ass_1_3}"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "json": lambda: {
                        "success": True,
                        "value": [
                            {
                                "student_id": student_id,
                                "path": f"/submitted/no_course/{ass_1_3}/1/",
                                "timestamp": "2020-01-01 00:00:00.0 UTC",
                            }
                        ],
                    },
                },
            )
        else:
            assert collection is False
            collection = True
            assert args[0] == (
                f"collection?course_id=no_course&assignment_id={ass_1_3}&path=%2Fsubmitted%2Fno_course%2F{ass_1_3}%2F1%2F"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(
                    notebook1_filename, arcname=os.path.basename(notebook1_filename)
                )
                # tar_handle.add(notebook2_filename, arcname=os.path.basename(notebook2_filename))
            tar_file.seek(0)

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
        assert collections and collection
        assert os.path.exists(
            os.path.join(
                plugin.coursedir.format_path(
                    plugin_config.CourseDirectory.submitted_directory,
                    student_id,
                    ass_1_3,
                ),
                os.path.basename(notebook1_filename),
            )
        )


@pytest.mark.gen_test
def test_collect_normal_update(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = ass_1_2
    plugin_config.ExchangeCollect.update = True
    plugin_config.CourseDirectory.submitted_directory = str(
        tmpdir.mkdir("submitted").realpath()
    )
    plugin = ExchangeCollect(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )
    os.makedirs(
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory, student_id, ass_1_2
        ),
        exist_ok=True,
    )
    copyfile(
        notebook1_filename,
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory,
            student_id,
            ass_1_2,
            os.path.basename(notebook1_filename),
        ),
    )
    with open(
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory,
            student_id,
            ass_1_2,
            "timestamp.txt",
        ),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.000")

    collections = False
    collection = False

    def api_request(*args, **kwargs):
        nonlocal collections, collection
        tar_file = io.BytesIO()
        if "collections" in args[0]:
            assert collections is False
            collections = True
            assert args[0] == (
                f"collections?course_id=no_course&assignment_id={ass_1_2}"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "json": lambda: {
                        "success": True,
                        "value": [
                            {
                                "student_id": student_id,
                                "path": f"/submitted/no_course/{ass_1_2}/1/",
                                "timestamp": "2020-02-01 00:00:00.100",
                            }
                        ],
                    },
                },
            )
        else:
            assert collection is False
            collection = True
            assert args[0] == (
                f"collection?course_id=no_course&assignment_id={ass_1_2}&path=%2Fsubmitted%2Fno_course%2F{ass_1_2}%2F1%2F"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                # tar_handle.add(notebook1_filename, arcname=os.path.basename(notebook1_filename))
                tar_handle.add(
                    notebook2_filename, arcname=os.path.basename(notebook2_filename)
                )
            tar_file.seek(0)

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
        assert collections and collection
        assert not os.path.exists(
            os.path.join(
                plugin.coursedir.format_path(
                    plugin_config.CourseDirectory.submitted_directory,
                    student_id,
                    ass_1_2,
                ),
                os.path.basename(notebook1_filename),
            )
        )
        assert os.path.exists(
            os.path.join(
                plugin.coursedir.format_path(
                    plugin_config.CourseDirectory.submitted_directory,
                    student_id,
                    ass_1_2,
                ),
                os.path.basename(notebook2_filename),
            )
        )


@pytest.mark.gen_test
def test_collect_normal_dont_update(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = ass_1_4
    plugin_config.ExchangeCollect.update = False
    plugin_config.CourseDirectory.submitted_directory = str(
        tmpdir.mkdir("submitted").realpath()
    )
    plugin = ExchangeCollect(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )
    os.makedirs(
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory, student_id, ass_1_4
        ),
        exist_ok=True,
    )
    copyfile(
        notebook1_filename,
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory,
            student_id,
            ass_1_4,
            os.path.basename(notebook1_filename),
        ),
    )
    with open(
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory,
            student_id,
            ass_1_4,
            "timestamp.txt",
        ),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.000")

    collections = False
    collection = False

    def api_request(*args, **kwargs):
        nonlocal collections, collection
        tar_file = io.BytesIO()
        if "collections" in args[0]:
            assert collections is False
            collections = True
            assert args[0] == (
                f"collections?course_id=no_course&assignment_id={ass_1_4}"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "json": lambda: {
                        "success": True,
                        "value": [
                            {
                                "student_id": student_id,
                                "path": f"/submitted/no_course/{ass_1_4}/1/",
                                "timestamp": "2020-02-01 00:00:00.100",
                            }
                        ],
                    },
                },
            )
        else:
            assert collection is False
            collection = True
            assert args[0] == (
                f"collection?course_id=no_course&assignment_id={ass_1_4}&path=%2Fsubmitted%2Fno_course%2F{ass_1_4}%2F1%2F"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                # tar_handle.add(notebook1_filename, arcname=os.path.basename(notebook1_filename))
                tar_handle.add(
                    notebook2_filename, arcname=os.path.basename(notebook2_filename)
                )
            tar_file.seek(0)

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
        assert collections and not collection
        assert os.path.exists(
            os.path.join(
                plugin.coursedir.format_path(
                    plugin_config.CourseDirectory.submitted_directory,
                    student_id,
                    ass_1_4,
                ),
                os.path.basename(notebook1_filename),
            )
        )
        assert not os.path.exists(
            os.path.join(
                plugin.coursedir.format_path(
                    plugin_config.CourseDirectory.submitted_directory,
                    student_id,
                    ass_1_4,
                ),
                os.path.basename(notebook2_filename),
            )
        )


@pytest.mark.gen_test
def test_collect_normal_dont_update_old(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = ass_1_5
    plugin_config.ExchangeCollect.update = True
    plugin_config.CourseDirectory.submitted_directory = str(
        tmpdir.mkdir("submitted").realpath()
    )
    plugin = ExchangeCollect(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )
    os.makedirs(
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory, student_id, ass_1_5
        ),
        exist_ok=True,
    )
    copyfile(
        notebook1_filename,
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory,
            student_id,
            ass_1_5,
            os.path.basename(notebook1_filename),
        ),
    )
    with open(
        os.path.join(
            plugin_config.CourseDirectory.submitted_directory,
            student_id,
            ass_1_5,
            "timestamp.txt",
        ),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:01.000")

    collections = False
    collection = False

    def api_request(*args, **kwargs):
        nonlocal collections, collection
        tar_file = io.BytesIO()
        if "collections" in args[0]:
            assert collections is False
            collections = True
            assert args[0] == (
                f"collections?course_id=no_course&assignment_id={ass_1_5}"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "json": lambda: {
                        "success": True,
                        "value": [
                            {
                                "student_id": student_id,
                                "path": f"/submitted/no_course/{ass_1_5}/1/",
                                "timestamp": "2020-01-01 00:00:00.100",
                            }
                        ],
                    },
                },
            )
        else:
            assert collection is False
            collection = True
            assert args[0] == (
                f"collection?course_id=no_course&assignment_id={ass_1_5}&path=%2Fsubmitted%2Fno_course%2F{ass_1_5}%2F1%2F"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                # tar_handle.add(notebook1_filename, arcname=os.path.basename(notebook1_filename))
                tar_handle.add(
                    notebook2_filename, arcname=os.path.basename(notebook2_filename)
                )
            tar_file.seek(0)

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
        assert collections and not collection
        assert os.path.exists(
            os.path.join(
                plugin.coursedir.format_path(
                    plugin_config.CourseDirectory.submitted_directory,
                    student_id,
                    ass_1_5,
                ),
                os.path.basename(notebook1_filename),
            )
        )
        assert not os.path.exists(
            os.path.join(
                plugin.coursedir.format_path(
                    plugin_config.CourseDirectory.submitted_directory,
                    student_id,
                    ass_1_5,
                ),
                os.path.basename(notebook2_filename),
            )
        )


@pytest.mark.gen_test
def test_collect_normal_several(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = ass_1_1
    plugin_config.CourseDirectory.submitted_directory = str(
        tmpdir.mkdir("submitted").realpath()
    )
    plugin = ExchangeCollect(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )
    collections = False
    collection = False

    def api_request(*args, **kwargs):
        nonlocal collections, collection
        tar_file = io.BytesIO()
        if "collections" in args[0]:
            assert collections is False
            collections = True
            assert args[0] == (
                f"collections?course_id=no_course&assignment_id={ass_1_1}"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "json": lambda: {
                        "success": True,
                        "value": [
                            {
                                "student_id": student_id,
                                "path": f"/submitted/no_course/{ass_1_1}/1/",
                                "timestamp": "2020-01-01 00:00:00.0 UTC",
                            }
                        ],
                    },
                },
            )
        else:
            assert collection is False
            collection = True
            assert args[0] == (
                f"collection?course_id=no_course&assignment_id={ass_1_1}&path=%2Fsubmitted%2Fno_course%2F{ass_1_1}%2F1%2F"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(
                    notebook1_filename, arcname=os.path.basename(notebook1_filename)
                )
                tar_handle.add(
                    notebook2_filename, arcname=os.path.basename(notebook2_filename)
                )
            tar_file.seek(0)

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
        assert collections and collection
        assert os.path.exists(
            os.path.join(
                plugin.coursedir.format_path(
                    plugin_config.CourseDirectory.submitted_directory,
                    student_id,
                    ass_1_1,
                ),
                os.path.basename(notebook1_filename),
            )
        )
        assert os.path.exists(
            os.path.join(
                plugin.coursedir.format_path(
                    plugin_config.CourseDirectory.submitted_directory,
                    student_id,
                    ass_1_1,
                ),
                os.path.basename(notebook2_filename),
            )
        )


@pytest.mark.gen_test
def test_collect_normal_gradebook_called(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = ass_1_3
    plugin_config.CourseDirectory.submitted_directory = str(
        tmpdir.mkdir("submitted").realpath()
    )
    plugin = ExchangeCollect(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )
    collections = False
    collection = False
    gradebook_called = False

    def gradebook_update(*args, **kwargs):
        nonlocal gradebook_called
        gradebook_called = True
        assert kwargs.get("first_name") == "First"
        assert kwargs.get("last_name") == "Surname"
        assert args[0] == student_id

    def api_request(*args, **kwargs):
        nonlocal collections, collection
        tar_file = io.BytesIO()
        if "collections" in args[0]:
            assert collections is False
            collections = True
            assert args[0] == (
                f"collections?course_id=no_course&assignment_id={ass_1_3}"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "json": lambda: {
                        "success": True,
                        "value": [
                            {
                                "student_id": student_id,
                                "full_name": "First Surname",
                                "path": f"/submitted/no_course/{ass_1_3}/1/",
                                "timestamp": "2020-01-01 00:00:00.0 UTC",
                            }
                        ],
                    },
                },
            )
        else:
            assert collection is False
            collection = True
            assert args[0] == (
                f"collection?course_id=no_course&assignment_id={ass_1_3}&path=%2Fsubmitted%2Fno_course%2F{ass_1_3}%2F1%2F"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(
                    notebook1_filename, arcname=os.path.basename(notebook1_filename)
                )
                # tar_handle.add(notebook2_filename, arcname=os.path.basename(notebook2_filename))
            tar_file.seek(0)

            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "content": tar_file.read(),
                },
            )

    with patch.object(Exchange, "api_request", side_effect=api_request), patch.object(
        Gradebook, "update_or_create_student", side_effect=gradebook_update
    ):
        plugin.start()
        assert gradebook_called
        assert collections and collection
        assert os.path.exists(
            os.path.join(
                plugin.coursedir.format_path(
                    plugin_config.CourseDirectory.submitted_directory,
                    student_id,
                    ass_1_3,
                ),
                os.path.basename(notebook1_filename),
            )
        )


@pytest.mark.gen_test
def test_collect_normal_gradebook_called_no_space(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = ass_1_3
    plugin_config.CourseDirectory.submitted_directory = str(
        tmpdir.mkdir("submitted").realpath()
    )
    plugin = ExchangeCollect(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )
    collections = False
    collection = False
    gradebook_called = False

    def gradebook_update(*args, **kwargs):
        nonlocal gradebook_called
        gradebook_called = True
        assert kwargs.get("first_name") == "First"
        assert kwargs.get("last_name") == ""
        assert args[0] == student_id

    def api_request(*args, **kwargs):
        nonlocal collections, collection
        tar_file = io.BytesIO()
        if "collections" in args[0]:
            assert collections is False
            collections = True
            assert args[0] == (
                f"collections?course_id=no_course&assignment_id={ass_1_3}"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "json": lambda: {
                        "success": True,
                        "value": [
                            {
                                "student_id": student_id,
                                "full_name": "First",
                                "path": f"/submitted/no_course/{ass_1_3}/1/",
                                "timestamp": "2020-01-01 00:00:00.0 UTC",
                            }
                        ],
                    },
                },
            )
        else:
            assert collection is False
            collection = True
            assert args[0] == (
                f"collection?course_id=no_course&assignment_id={ass_1_3}&path=%2Fsubmitted%2Fno_course%2F{ass_1_3}%2F1%2F"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(
                    notebook1_filename, arcname=os.path.basename(notebook1_filename)
                )
                # tar_handle.add(notebook2_filename, arcname=os.path.basename(notebook2_filename))
            tar_file.seek(0)

            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "content": tar_file.read(),
                },
            )

    with patch.object(Exchange, "api_request", side_effect=api_request), patch.object(
        Gradebook, "update_or_create_student", side_effect=gradebook_update
    ):
        plugin.start()
        assert gradebook_called
        assert collections and collection
        assert os.path.exists(
            os.path.join(
                plugin.coursedir.format_path(
                    plugin_config.CourseDirectory.submitted_directory,
                    student_id,
                    ass_1_3,
                ),
                os.path.basename(notebook1_filename),
            )
        )


@pytest.mark.gen_test
def test_collect_normal_gradebook_called_no_full_name(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = ass_1_3
    plugin_config.CourseDirectory.submitted_directory = str(
        tmpdir.mkdir("submitted").realpath()
    )
    plugin = ExchangeCollect(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )
    collections = False
    collection = False
    gradebook_called = False

    def gradebook_update(*args, **kwargs):
        nonlocal gradebook_called
        gradebook_called = True
        assert kwargs.get("first_name") == ""
        assert kwargs.get("last_name") == ""
        assert args[0] == student_id

    def api_request(*args, **kwargs):
        nonlocal collections, collection
        tar_file = io.BytesIO()
        if "collections" in args[0]:
            assert collections is False
            collections = True
            assert args[0] == (
                f"collections?course_id=no_course&assignment_id={ass_1_3}"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "json": lambda: {
                        "success": True,
                        "value": [
                            {
                                "student_id": student_id,
                                "path": f"/submitted/no_course/{ass_1_3}/1/",
                                "timestamp": "2020-01-01 00:00:00.0 UTC",
                            }
                        ],
                    },
                },
            )
        else:
            assert collection is False
            collection = True
            assert args[0] == (
                f"collection?course_id=no_course&assignment_id={ass_1_3}&path=%2Fsubmitted%2Fno_course%2F{ass_1_3}%2F1%2F"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(
                    notebook1_filename, arcname=os.path.basename(notebook1_filename)
                )
                # tar_handle.add(notebook2_filename, arcname=os.path.basename(notebook2_filename))
            tar_file.seek(0)

            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "content": tar_file.read(),
                },
            )

    with patch.object(Exchange, "api_request", side_effect=api_request), patch.object(
        Gradebook, "update_or_create_student", side_effect=gradebook_update
    ):
        plugin.start()
        assert gradebook_called
        assert collections and collection
        assert os.path.exists(
            os.path.join(
                plugin.coursedir.format_path(
                    plugin_config.CourseDirectory.submitted_directory,
                    student_id,
                    ass_1_3,
                ),
                os.path.basename(notebook1_filename),
            )
        )


@pytest.mark.gen_test
def test_collect_normal_several_gradebook_called(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = ass_1_1
    plugin_config.CourseDirectory.submitted_directory = str(
        tmpdir.mkdir("submitted").realpath()
    )
    plugin = ExchangeCollect(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )
    collections = False
    collection = False
    gradebook_called = False
    first_names = ["First", "Second"]
    last_names = ["Surname", "Lastname"]
    student_ids = ["1", "2"]
    collection_number = 0

    def gradebook_update(*args, **kwargs):
        nonlocal gradebook_called, collection_number
        gradebook_called = True
        assert kwargs.get("first_name") == first_names[collection_number]
        assert kwargs.get("last_name") == last_names[collection_number]
        assert args[0] == student_ids[collection_number]
        collection_number += 1

    def api_request(*args, **kwargs):
        nonlocal collections, collection
        tar_file = io.BytesIO()
        if "collections" in args[0]:
            collections = True
            assert args[0] == (
                f"collections?course_id=no_course&assignment_id={ass_1_1}"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "json": lambda: {
                        "success": True,
                        "value": [
                            {
                                "student_id": student_ids[0],
                                "full_name": "First Surname",
                                "path": f"/submitted/no_course/{ass_1_1}/1/",
                                "timestamp": "2020-01-01 00:00:00.0 UTC",
                            },
                            {
                                "student_id": student_ids[1],
                                "full_name": "Second Lastname",
                                "path": f"/submitted/no_course/{ass_1_1}/2/",
                                "timestamp": "2020-01-01 00:00:00.1 UTC",
                            },
                        ],
                    },
                },
            )
        else:
            num = "2" if collection else "1"
            assert args[0] == (
                f"collection?course_id=no_course&assignment_id={ass_1_1}&path=%2Fsubmitted%2Fno_course%2F{ass_1_1}%2F{num}%2F"
            )
            collection = True
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(
                    notebook1_filename, arcname=os.path.basename(notebook1_filename)
                )
            tar_file.seek(0)

            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "content": tar_file.read(),
                },
            )

    with patch.object(Exchange, "api_request", side_effect=api_request), patch.object(
        Gradebook, "update_or_create_student", side_effect=gradebook_update
    ):
        plugin.start()
        assert gradebook_called
        assert collection_number == 2
        assert collections and collection


@pytest.mark.gen_test
def test_collect_normal_several_full_name_none(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = ass_1_1
    plugin_config.CourseDirectory.submitted_directory = str(
        tmpdir.mkdir("submitted").realpath()
    )
    plugin = ExchangeCollect(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )
    collections = False
    collection = False
    gradebook_called = False
    student_ids = ["1", "2"]
    collection_number = 0

    def gradebook_update(*args, **kwargs):
        nonlocal gradebook_called, collection_number
        gradebook_called = True
        assert kwargs.get("first_name") == ""
        assert kwargs.get("last_name") == ""
        assert args[0] == student_ids[collection_number]
        collection_number += 1

    def api_request(*args, **kwargs):
        nonlocal collections, collection
        tar_file = io.BytesIO()
        if "collections" in args[0]:
            collections = True
            assert args[0] == (
                f"collections?course_id=no_course&assignment_id={ass_1_1}"
            )
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "json": lambda: {
                        "success": True,
                        "value": [
                            {
                                "student_id": student_ids[0],
                                "full_name": None,
                                "path": f"/submitted/no_course/{ass_1_1}/1/",
                                "timestamp": "2020-01-01 00:00:00.0 UTC",
                            },
                            {
                                "student_id": student_ids[1],
                                "full_name": None,
                                "path": f"/submitted/no_course/{ass_1_1}/2/",
                                "timestamp": "2020-01-01 00:00:00.1 UTC",
                            },
                        ],
                    },
                },
            )
        else:
            num = "2" if collection else "1"
            assert args[0] == (
                f"collection?course_id=no_course&assignment_id={ass_1_1}&path=%2Fsubmitted%2Fno_course%2F{ass_1_1}%2F{num}%2F"
            )
            collection = True
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(
                    notebook1_filename, arcname=os.path.basename(notebook1_filename)
                )
            tar_file.seek(0)

            return type(
                "Response",
                (object,),
                {
                    "status_code": 200,
                    "headers": {"content-type": "application/x-tar"},
                    "content": tar_file.read(),
                },
            )

    with patch.object(Exchange, "api_request", side_effect=api_request), patch.object(
        Gradebook, "update_or_create_student", side_effect=gradebook_update
    ):
        plugin.start()
        assert gradebook_called
        assert collection_number == 2
        assert collections and collection
