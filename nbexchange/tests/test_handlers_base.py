import logging
import re

import pytest

from nbexchange.tests.utils import async_requests

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


class BaseTestHandlers(object):
    pass


class TestHandlersBasic(BaseTestHandlers):

    # #### basic "does service exist" tests #### #
    # Test that the base endpoint returns a text string (ie the end-point is alive)
    @pytest.mark.gen_test
    def test_main_page(self, app):
        r = yield async_requests.get(app.url + "/")
        assert r.status_code == 200
        assert re.search(r"NbExchange", r.text)

    def test_base_location_story(self, app):
        # Not "/services/nbexchange/", the tests move it
        assert app.base_storage_location in ["/tmp/exchange/", "/tmp/courses"]
