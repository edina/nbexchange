import json
import logging
import pytest
import re
import sys

from mock import patch
from nbexchange.app import NbExchange
from nbexchange.base import BaseHandler
from nbexchange.tests.test_handlers_base import BaseTestHandlers
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


class TestHandlersFetch(BaseTestHandlers):
    """ GET /assignments (list assignments)
    """

    # require authenticated user (404 because the bounce to login fails)
    @pytest.mark.gen_test
    def test_assignments0(self, app):
        r = yield async_requests.get(app.url + "/assignments")
        assert r.status_code == 404

    # Requires a course_id param
    @pytest.mark.gen_test
    def test_assignments1(self, app):
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz):
            with patch.object(BaseHandler, "get_auth_state", return_value=auth_inst):
                r = yield async_requests.get(app.url + "/assignments")
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["success"] == False
        assert response_data["note"] == "Assigment call requires a course id"

    # test when not subscribed
    @pytest.mark.gen_test
    def test_assignments2(self, app):
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz):
            with patch.object(BaseHandler, "get_auth_state", return_value=auth_inst):
                r = yield async_requests.get(
                    app.url + "/assignments?course_id=course_a"
                )
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["success"] == False
        assert response_data["note"] == "User not subscribed to course course_a"

    # test when subscribed
    @pytest.mark.gen_test
    def test_assignments3(self, app):
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz):
            with patch.object(BaseHandler, "get_auth_state", return_value=auth_inst):
                r = yield async_requests.get(
                    app.url + "/assignments?course_id=course_2"
                )
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["success"] == True
        assert "note" not in response_data  # just that it's missing
        assert (
            "value" in response_data
        )  # just that it's present (it will have no content)
