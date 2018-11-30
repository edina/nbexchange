import re

import pytest
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from nbexchange import apihandlers
from nbexchange.app import NbExchange
from nbexchange.base import BaseHandler
from nbexchange.tests.utils import async_requests

import logging

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


def _resolve_url(page_url, url):
    """Resolve a URL relative to a page"""

    # full URL, nothing to resolve
    if "://" in url:
        return url

    parsed = urlparse(page_url)

    if url.startswith("/"):
        # absolute path
        return f"{parsed.scheme}://{parsed.netloc}{url}"

    # relative path URL

    if page_url.endswith("/"):
        # URL is a directory, resolve relative to dir
        path = parsed.path
    else:
        # URL is not a directory, resolve relative to parent
        path = parsed.path.rsplit("/", 1)[0] + "/"

    return f"{parsed.scheme}://{parsed.netloc}{path}{url}"


@pytest.mark.gen_test
@pytest.mark.remote
def test_main_page(app):
    """Check the main page"""
    r = yield async_requests.get(app.url + "/")
    assert r.status_code == 200
    assert re.search(r"Hello World, this is home", r.text)


@pytest.mark.gen_test
@pytest.mark.remote
def test_env_page(app):
    """Check the environment page"""
    r = yield async_requests.get(app.url + "/env")
    assert r.status_code == 200

    soup = BeautifulSoup(r.text, "html5lib")

    title = soup.find_all(text="Environment")
    assert len(title) >= 1


@pytest.mark.gen_test
@pytest.mark.remote
def test_user_page_unauthenticated(app):
    """Check the user page"""
    r = yield async_requests.get(app.url + "/user")
    assert r.status_code == 404
