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

##### POST /assignment (upload/release assignment) ######

# require authenticated user (404 because the bounce to login fails)
@pytest.mark.gen_test
def test_post_assignment0(app):
    r = yield async_requests.post(app.url + "/assignment")
    assert r.status_code == 403  # why not 404???


# set up the file to be uploaded
filename = sys.argv[0]  # ourself :)
tar_file = tar_source(filename)
files = {"assignment": ("assignment.tar.gz", tar_file)}

# Requires both params (none)
@pytest.mark.gen_test
def test_post_assignment1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + "/assignment")
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Posting an Assigment requires a course code and an assignment code"
    )


# Requires both params (just course)
@pytest.mark.gen_test
def test_post_assignment2(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + "/assignment?course_id=course_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Posting an Assigment requires a course code and an assignment code"
    )


# Requires both params (just assignment)
@pytest.mark.gen_test
def test_post_assignment3(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + "/assignment?assignment_id=assign_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Posting an Assigment requires a course code and an assignment code"
    )


# Student cannot release
@pytest.mark.gen_test
def test_post_assignment4(app):
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "User not an instructor to course course_2"


# # instructor can release
# @pytest.mark.gen_test
# def test_post_assignment5(app):
#     with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor
#     ):
#
#             r = yield async_requests.post(
#                 app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
#                 files=files,
#             )
#     assert r.status_code == 200
#     response_data = r.json()
#     assert response_data["success"] == True
#     assert response_data["note"] == "Released"


# fails if no file is part of post request
@pytest.mark.gen_test
def test_post_assignment6(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a"
        )
    assert r.status_code == 412


# Instructor, wrong course, cannot release
@pytest.mark.gen_test
def test_post_assignment7(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_1&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "User not subscribed to course course_1"


# instructor releasing - Picks up the first attribute if more than 1 (wrong course)
@pytest.mark.gen_test
def test_post_assignment8(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + "/assignment?course_id=course_1&course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "User not subscribed to course course_1"


# # instructor releasing - Picks up the first attribute if more than 1 (right course)
# @pytest.mark.gen_test
# def test_post_assignment9(app):
#     with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
#             r = yield async_requests.post(
#                 app.url
#                 + "/assignment?course_id=course_2&course_id=course_1&assignment_id=assign_a",
#                 files=files,
#             )
#     assert r.status_code == 200
#     response_data = r.json()
#     assert response_data["success"] == True
#     assert response_data["note"] == "Released"
