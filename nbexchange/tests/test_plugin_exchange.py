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
        parts = os.path.split(dir_name)
        struct = dir_structure
        for part in parts:
            struct = struct[part]
        return list(struct)
    return inner


def fake_isdir(dir_structure):
    def inner(dir_name):
        parts = os.path.split(dir_name)
        struct = dir_structure
        for part in parts:
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

    dir_struct = {}

    # with (patch("nbexchange.plugin.exchange.os.path.isdir", fake_isdir(dir_struct)),
    #       patch("nbexchange.plugin.exchange.os.listdir", fake_listdir(dir_struct))):
    structure = plugin.get_directory_structure("assignments")
    assert structure == ["assignments", "{student_id}", "{assignment_id}"]
    structure = plugin.get_directory_structure("assignments", user_id="1")
    assert structure == [os.path.join("assignments", "1"), "{assignment_id}"]
    structure = plugin.get_directory_structure("assignments", user_id="1", assignment_id="123")
    assert structure == [os.path.join("assignments", "1", "123")]
    structure = plugin.get_directory_structure("assignments", assignment_id="123")
    assert structure == ["assignments", "{student_id}", "123"]
