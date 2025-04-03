import io
import logging
import os
import tarfile
from shutil import copyfile

import pytest
import requests
from mock import patch
from nbgrader.coursedir import CourseDirectory
from nbgrader.exchange import ExchangeError

from nbexchange.plugin import Exchange

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

"""
In this module we check that various helper methods in the Exchange base class works as expected.
In particular, we're checking that the api_request method does the right thing, as we will
be mocking it when testing the other classes.
"""


@pytest.mark.gen_test
def test_defaults():
    plugin = Exchange()

    assert plugin.path_includes_course is False
    assert plugin.assignment_dir == "."
    assert plugin.base_service_url == "https://noteable.edina.ac.uk"
    assert plugin.service_url() == "https://noteable.edina.ac.uk/services/nbexchange/"
    assert plugin.course_id == "no_course"
    assert plugin.max_buffer_size == 5253530000
    assert plugin.api_timeout == 10


@pytest.mark.gen_test
def test_base_methods(monkeypatch):
    monkeypatch.setenv("NAAS_BASE_URL", "https://example.com")
    assert os.environ.get("NAAS_BASE_URL") == "https://example.com"
    plugin = Exchange()
    # assert plugin.service_url() == "https://example.com/services/nbexchange/"

    with pytest.raises(ExchangeError) as my_failure:
        plugin.fail("some random text")
    assert "some random text" in str(my_failure.value)

    with pytest.raises(NotImplementedError):
        plugin.init_src()

    with pytest.raises(NotImplementedError):
        plugin.init_dest()

    with pytest.raises(NotImplementedError):
        plugin.copy_files()

    with pytest.raises(NotImplementedError):
        plugin.do_copy("a", "b")

    with pytest.raises(NotImplementedError):
        plugin.start()


@pytest.mark.gen_test
def test_exhange_api_request_post():

    plugin = Exchange()

    def asserts(*args, **kwargs):
        assert "cookies" in kwargs
        assert "noteable_auth" in kwargs["cookies"]
        assert kwargs["cookies"]["noteable_auth"] == "test_token"
        assert "headers" in kwargs
        assert args[0] == plugin.service_url() + "test"
        return "Success"

    naas_token = os.environ.get("NAAS_JWT")
    os.environ["NAAS_JWT"] = "test_token"
    with patch("nbexchange.plugin.exchange.requests.post", side_effect=asserts):
        called = plugin.api_request("test", method="POST")
        assert called == "Success"
    if naas_token is not None:
        os.environ["NAAS_JWT"] = naas_token
    else:
        del os.environ["NAAS_JWT"]


@pytest.mark.gen_test
def test_exhange_api_request_delete():
    plugin = Exchange()

    def asserts(*args, **kwargs):
        assert "cookies" in kwargs
        assert "noteable_auth" in kwargs["cookies"]
        assert kwargs["cookies"]["noteable_auth"] == "test_token"
        assert "headers" in kwargs
        assert args[0] == plugin.service_url() + "test"
        return "Success"

    naas_token = os.environ.get("NAAS_JWT")
    os.environ["NAAS_JWT"] = "test_token"
    with patch("nbexchange.plugin.exchange.requests.delete", side_effect=asserts):
        called = plugin.api_request("test", method="DELETE")
        assert called == "Success"
    if naas_token is not None:
        os.environ["NAAS_JWT"] = naas_token
    else:
        del os.environ["NAAS_JWT"]


@pytest.mark.gen_test
def test_exhange_api_request_get():
    plugin = Exchange()

    def asserts(*args, **kwargs):
        assert "cookies" in kwargs
        assert "noteable_auth" in kwargs["cookies"]
        assert kwargs["cookies"]["noteable_auth"] == "test_token"
        assert "headers" in kwargs
        assert args[0] == plugin.service_url() + "test"
        return "Success"

    naas_token = os.environ.get("NAAS_JWT")
    os.environ["NAAS_JWT"] = "test_token"
    with patch("nbexchange.plugin.exchange.requests.get", side_effect=asserts):
        called = plugin.api_request("test")
        assert called == "Success"
    if naas_token is not None:
        os.environ["NAAS_JWT"] = naas_token
    else:
        del os.environ["NAAS_JWT"]


@pytest.mark.gen_test
def test_exhange_api_request_get_timeout():
    plugin = Exchange()

    plugin.api_timeout = 2
    naas_token = os.environ.get("NAAS_JWT")
    os.environ["NAAS_JWT"] = "test_token"
    with patch("nbexchange.plugin.exchange.requests.get", side_effect=requests.exceptions.Timeout):
        with pytest.raises(requests.exceptions.Timeout):
            plugin.api_request("test")
    if naas_token is not None:
        os.environ["NAAS_JWT"] = naas_token
    else:
        del os.environ["NAAS_JWT"]


@pytest.mark.gen_test
def test_add_to_tar_honours_ignore_list(plugin_config, tmpdir):

    notebook1_filename = os.path.join(os.path.dirname(__file__), "data", "assignment-0.6.ipynb")
    release_dir = "release_test"
    plugin_config.CourseDirectory.release_directory = str(tmpdir.mkdir(release_dir).realpath())
    main_dir = os.path.join(plugin_config.CourseDirectory.release_directory, "assign_1")
    feedback_dir = os.path.join(main_dir, "feedback")
    checkpoints_dir = os.path.join(main_dir, ".ipynb_checkpoints")
    pycache_dir = os.path.join(main_dir, "__pycache__")

    os.makedirs(feedback_dir, exist_ok=True)
    os.makedirs(checkpoints_dir, exist_ok=True)
    os.makedirs(pycache_dir, exist_ok=True)

    # main file
    copyfile(
        notebook1_filename,
        os.path.join(
            main_dir,
            "release1.ipynb",
        ),
    )
    # some other file
    with open(
        os.path.join(main_dir, "timestamp.txt"),
        "w",
    ) as fp:
        fp.write("2020-01-01 00:00:00.0 UTC")

    # checkpoint, should be ignored - yes, the file has the wrong name
    copyfile(
        notebook1_filename,
        os.path.join(
            checkpoints_dir,
            "release1_checkpoint.ipynb",
        ),
    )

    # feedback, should be ignored - yes, the file has the wrong name
    copyfile(
        notebook1_filename,
        os.path.join(
            feedback_dir,
            "release1_checkpoint.ipynb",
        ),
    )

    # cache_dir, should be ignored - yes, the file has the wrong name
    copyfile(
        notebook1_filename,
        os.path.join(
            pycache_dir,
            "release1_checkpoint.ipynb",
        ),
    )
    plugin = Exchange(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
    print(plugin.max_buffer_size)
    # Without the ignore pattern included, we tar up all 5 files
    tar_file = io.BytesIO()
    with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
        plugin.add_to_tar(tar_handle, main_dir)
    tar_file.seek(0)
    with tarfile.open(fileobj=tar_file) as handle:
        assert len(handle.getmembers()) == 5

    # With the ignore pattern included, we only tar up 2 files
    tar_file = io.BytesIO()
    with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
        plugin.add_to_tar(tar_handle, main_dir, plugin.coursedir.ignore)
    tar_file.seek(0)
    with tarfile.open(fileobj=tar_file) as handle:
        assert len(handle.getmembers()) == 2
