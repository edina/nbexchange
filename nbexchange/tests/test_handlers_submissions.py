import logging
import pytest

from mock import patch
from nbexchange.handlers.base import BaseHandler
from nbexchange.tests.utils import (
    async_requests,
    user_kiz_instructor,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

##### POST /submissions ######
# No method available (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_assignments0(app):
    with patch.object(BaseHandler, "get_current_user", return_value={}):
        r = yield async_requests.post(app.url + "/submissions")
    assert r.status_code == 501


# subscribed user makes no difference (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_assignments1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + "/submissions?course_id=course_2")
    assert r.status_code == 501


##### GET /submissions  ######
# No method available (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_submissions0(app):
    r = yield async_requests.get(app.url + "/submissions")
    assert r.status_code == 501


# subscribed user makes no difference (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_submissions1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/submissions?course_id=course_2")
    assert r.status_code == 501
