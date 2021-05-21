import logging
import os

import pytest
from mock import patch
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

    assert plugin.path_includes_course == False
    assert plugin.assignment_dir == "."
    assert plugin.base_service_url == "https://noteable.edina.ac.uk"
    assert plugin.service_url() == "https://noteable.edina.ac.uk/services/nbexchange/"
    assert plugin.course_id == "no_course"
    assert plugin.max_buffer_size == 5253530000


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


## Not sure how to test this just now
@pytest.mark.gen_test
def test_exhange__assignment_not_found():
    pass
