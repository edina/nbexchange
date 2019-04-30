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
    user_kiz_instructor,
    user_brobbere_instructor,
    user_kiz_student,
    user_brobbere_student,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

##### GET /submission ######
# No method available (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_submission0(app):
    r = yield async_requests.get(app.url + "/submission")
    assert r.status_code == 501


# subscribed user makes no difference (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_submission1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/submission?course_id=course_2")
    assert r.status_code == 501


##### POST /submission (submit assignment) ######

# require authenticated user (404 because the bounce to login fails)
@pytest.mark.gen_test
def test_post_assignments0(app):
    with patch.object(BaseHandler, "get_current_user", return_value={}):
        r = yield async_requests.post(app.url + "/submission")
    assert r.status_code == 403


# Requires both params (none)
@pytest.mark.gen_test
def test_post_submision1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + "/submission")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Submission call requires both a course code and an assignment code"
    )


# Requires both params (just course)
@pytest.mark.gen_test
def test_post_submision2(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + "/submission?course_id=course_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Submission call requires both a course code and an assignment code"
    )


# Requires both params (just assignment)
@pytest.mark.gen_test
def test_post_submision3(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + "/submission?assignment_id=assign_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Submission call requires both a course code and an assignment code"
    )


# User not fetched assignment
@pytest.mark.gen_test
def test_post_submision4(app):
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_c"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "User not fetched assignment assign_c"


# # Student can submit
# @pytest.mark.gen_test
# def test_post_submision4(app):
#     with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
#             r = yield async_requests.post(
#                 app.url + "/submission?course_id=course_2&assignment_id=assign_a",
#                 files=files,
#             )
#     assert r.status_code == 200
#     response_data = r.json()
#     assert response_data["success"] == True
#     assert response_data["note"] == "Submitted"


# # instructor can submit
# @pytest.mark.gen_test
# def test_post_submision5(app):
#     with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
# #             r = yield async_requests.post(
#                 app.url + "/submission?course_id=course_2&assignment_id=assign_a",
#                 files=files,
#             )
#     assert r.status_code == 200
#     response_data = r.json()
#     assert response_data["success"] == True
#     assert response_data["note"] == "Submitted"


# # fails if no file is part of post request
# @pytest.mark.gen_test
# def test_post_submision4(app):
#     with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
#             r = yield async_requests.post(
#                 app.url + "/submission?course_id=course_2&assignment_id=assign_a"
#             )
#     assert r.status_code == 412


# # Picks up the first attribute if more than 1 (wrong course)
# @pytest.mark.gen_test
# def test_post_submision4(app):
#     with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
#             r = yield async_requests.post(
#                 app.url
#                 + "/submission?course_id=course_1&course_2&assignment_id=assign_a",
#                 files=files,
#             )
#     assert r.status_code == 200
#     response_data = r.json()
#     assert response_data["success"] == False
#     assert response_data["note"] == "Submitted"


# # Picks up the first attribute if more than 1 (right course)
# @pytest.mark.gen_test
# def test_post_submision4(app):
#     with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
#             r = yield async_requests.post(
#                 app.url + "/submission?course_id=course_2&assignment_id=assign_a",
#                 files=files,
#             )
#     assert r.status_code == 200
#     response_data = r.json()
#     assert response_data["success"] == True
#     assert response_data["note"] == "Submitted"
