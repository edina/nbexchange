import logging
import re

import pytest

from nbexchange.tests.utils import async_requests

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


class BaseTestHandlers(object):
    pass


class TestHandlersBasic(BaseTestHandlers):
    ##### basic "does service exist" tests #####
    # Test that the base endpoint returns a text string (ie the end-point is alive)
    @pytest.mark.gen_test
    def test_main_page(self, app):
        r = yield async_requests.get(app.url + "/")
        assert r.status_code == 200
        assert re.search(r"NbExchange", r.text)

    #### Not working
    # # we can define a datasbe name
    # @pytest.mark.gen_test
    # def test_different_db_name(app, monkeypatch):
    #     monkeypatch.setitem(os.environ, 'NBEX_DB_DATABASE', 'kiz_test.sqlite')
    #     print(f"db_url: {app.db_url}")
    #     r = yield async_requests.get(app.url + "/")
    #     assert r.status_code == 200
    #     assert re.search(r"NbExchange", r.text)

    #     assert os.path.isfile('kiz_test.sqlite')
    #     #os.remove('kiz_test.sqlite')
    #     #assert not os.path.isfile('kiz_test.sqlite')
    #     monkeypatch.setitem(os.environ, 'NBEX_DB_DATABASE', '')
    #     reload(app)
