import pytest
import requests
from nbexchange import apihandlers
from nbexchange.app import NbExchange


@pytest.mark.gen_test
@pytest.mark.remote
def test_main_page(app, http_client):
    """Check the main page"""

    r = yield http_client.fetch(app.url + "/")
    assert r.code == 200


@pytest.mark.gen_test
@pytest.mark.remote
def test_user_endpoint(app, http_client):
    """Check the user page"""
    url = f"{app.url}/user/"
    r = yield http_client.fetch(url)
    assert r.code == 200
