import logging
import os

import pytest
import requests

from mock import patch

from nbexchange.plugin import Exchange
from nbgrader.coursedir import CourseDirectory

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


def fake_listdir(dir_structure):
    def inner(dir_name):
        parts = dir_name.split(os.path.sep)
        struct = dir_structure
        for part in parts:
            struct = struct[part]
        return list(struct)
    return inner


def fake_isdir(dir_structure):
    def inner(dir_name):
        parts = dir_name.split(os.path.sep)
        struct = dir_structure
        for part in parts:
            if part not in struct:
                struct = None
                break
            struct = struct[part]
        return isinstance(struct, dict) or isinstance(struct, list)
    return inner


"""
In this module we check that various helper methods in the Exchange base class works as expected.
In particular, we're checking that the api_request method does the right thing, as we will
be mocking it when testing the other classes.
"""


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
def test_exhange_get_directory_structure(plugin_config):
    # plugin_config.CourseDirectory.directory_structure = os.path.join("")
    plugin = Exchange(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    structure = plugin.get_directory_structure("assignments")
    assert structure == ["assignments", "{student_id}", "{assignment_id}"]
    structure = plugin.get_directory_structure("assignments", user_id="1")
    assert structure == [os.path.join("assignments", "1"), "{assignment_id}"]
    structure = plugin.get_directory_structure("assignments", user_id="1", assignment_id="123")
    assert structure == [os.path.join("assignments", "1", "123")]
    structure = plugin.get_directory_structure("assignments", assignment_id="123")
    assert structure == ["assignments", "{student_id}", "123"]



@pytest.mark.gen_test
def test_exhange_get_files(plugin_config):
    # plugin_config.CourseDirectory.directory_structure = os.path.join("")
    plugin = Exchange(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    dir_struct = {
        "assignments": {
            "user1": {
                "assign1": ["file1", "file2"]
            },
            "user2": {
                "assign1": ["file3", "file4"]
            }
        }
    }

    with patch("nbexchange.plugin.exchange.os.path.isdir", fake_isdir(dir_struct)), \
         patch("nbexchange.plugin.exchange.os.listdir", fake_listdir(dir_struct)):
        files = plugin.get_files(["assignments", "{student_id}", "{assignment_id}"])
        assert files == [{"details": {"student_id": "user1", "assignment_id": "assign1"}, "files": ["assignments/user1/assign1/file1", "assignments/user1/assign1/file2"]},
                         {"details": {"student_id": "user2", "assignment_id": "assign1"}, "files": ["assignments/user2/assign1/file3", "assignments/user2/assign1/file4"]}]

@pytest.mark.gen_test
def test_exhange_get_files_more_stuff(plugin_config):
    # plugin_config.CourseDirectory.directory_structure = os.path.join("")
    plugin = Exchange(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    dir_struct = {
        "assignments": {
            "user1": {
                "assign1": ["file1", "file2"],
                "assign2": ["file5", "file6"],
            },
            "user2": {
                "assign1": ["file3", "file4"],
                "assign3": ["file7", "file8"]
            },
            "user3": {
                "assign4": ["file9", "file10"],
                "assign5": ["file11", "file12"]
            }
        }
    }

    with patch("nbexchange.plugin.exchange.os.path.isdir", fake_isdir(dir_struct)), \
         patch("nbexchange.plugin.exchange.os.listdir", fake_listdir(dir_struct)):
        files = plugin.get_files(["assignments", "{student_id}", "{assignment_id}"])
        assert files == [{"details": {"student_id": "user1", "assignment_id": "assign1"}, "files": ["assignments/user1/assign1/file1", "assignments/user1/assign1/file2"]},
                         {"details": {"student_id": "user1", "assignment_id": "assign2"}, "files": ["assignments/user1/assign2/file5", "assignments/user1/assign2/file6"]},
                         {"details": {"student_id": "user2", "assignment_id": "assign1"}, "files": ["assignments/user2/assign1/file3", "assignments/user2/assign1/file4"]},
                         {"details": {"student_id": "user2", "assignment_id": "assign3"}, "files": ["assignments/user2/assign3/file7", "assignments/user2/assign3/file8"]},
                         {"details": {"student_id": "user3", "assignment_id": "assign4"}, "files": ["assignments/user3/assign4/file9", "assignments/user3/assign4/file10"]},
                         {"details": {"student_id": "user3", "assignment_id": "assign5"}, "files": ["assignments/user3/assign5/file11", "assignments/user3/assign5/file12"]}]


@pytest.mark.gen_test
def test_exhange_get_files_specific_user(plugin_config):
    # plugin_config.CourseDirectory.directory_structure = os.path.join("")
    plugin = Exchange(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    dir_struct = {
        "assignments": {
            "user1": {
                "assign1": ["file1", "file2"],
                "assign2": ["file5", "file6"],
            },
            "user2": {
                "assign1": ["file3", "file4"],
                "assign3": ["file7", "file8"]
            },
            "user3": {
                "assign4": ["file9", "file10"],
                "assign5": ["file11", "file12"]
            }
        }
    }

    with patch("nbexchange.plugin.exchange.os.path.isdir", fake_isdir(dir_struct)), \
         patch("nbexchange.plugin.exchange.os.listdir", fake_listdir(dir_struct)):
        files = plugin.get_files(["assignments", "user1", "{assignment_id}"])
        assert files == [{"details": {"assignment_id": "assign1"}, "files": ["assignments/user1/assign1/file1", "assignments/user1/assign1/file2"]},
                         {"details": {"assignment_id": "assign2"}, "files": ["assignments/user1/assign2/file5", "assignments/user1/assign2/file6"]},
                        ]

@pytest.mark.gen_test
def test_exhange_get_files_specific_assignment(plugin_config):
    # plugin_config.CourseDirectory.directory_structure = os.path.join("")
    plugin = Exchange(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    dir_struct = {
        "assignments": {
            "user1": {
                "assign1": ["file1", "file2"],
                "assign2": ["file5", "file6"],
            },
            "user2": {
                "assign1": ["file3", "file4"],
                "assign3": ["file7", "file8"]
            },
            "user3": {
                "assign4": ["file9", "file10"],
                "assign5": ["file11", "file12"]
            }
        }
    }

    with patch("nbexchange.plugin.exchange.os.path.isdir", fake_isdir(dir_struct)), \
         patch("nbexchange.plugin.exchange.os.listdir", fake_listdir(dir_struct)):
        files = plugin.get_files(["assignments", "{student_id}", "assign1"])
        assert files == [{"details": {"student_id": "user1"}, "files": ["assignments/user1/assign1/file1", "assignments/user1/assign1/file2"]},
                         {"details": {"student_id": "user2"}, "files": ["assignments/user2/assign1/file3", "assignments/user2/assign1/file4"]},
                        ]

@pytest.mark.gen_test
def test_exhange_get_files_single_folder(plugin_config):
    # plugin_config.CourseDirectory.directory_structure = os.path.join("")
    plugin = Exchange(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    dir_struct = {
        "assignments": {
            "user1": {
                "assign1": ["file1", "file2"],
                "assign2": ["file5", "file6"],
            },
            "user2": {
                "assign1": ["file3", "file4"],
                "assign3": ["file7", "file8"]
            },
            "user3": {
                "assign4": ["file9", "file10"],
                "assign5": ["file11", "file12"]
            }
        }
    }

    with patch("nbexchange.plugin.exchange.os.path.isdir", fake_isdir(dir_struct)), \
         patch("nbexchange.plugin.exchange.os.listdir", fake_listdir(dir_struct)):
        files = plugin.get_files(["assignments", "user1", "assign1"])
        assert files == [{"details": {}, "files": ["assignments/user1/assign1/file1", "assignments/user1/assign1/file2"]},
                        ]