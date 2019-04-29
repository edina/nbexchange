import json
import logging
import pytest
import re
import sys

from mock import patch
from nbexchange.app import NbExchange
from nbexchange.base import BaseHandler
from nbexchange.tests.utils import (
    async_requests,
    tar_source,
    user_kiz,
    user_bert,
    auth_inst,
    auth_stud,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

##### POST /submissions ######
# No method available (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_assignments0(app):
    r = yield async_requests.post(app.url + "/submissions")
    assert r.status_code == 501


# subscribed user makes no difference (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_assignments1(app):
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz):
        with patch.object(BaseHandler, "get_auth_state", return_value=auth_inst):
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
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz):
        with patch.object(BaseHandler, "get_auth_state", return_value=auth_inst):
            r = yield async_requests.get(app.url + "/submissions?course_id=course_2")
    assert r.status_code == 501
