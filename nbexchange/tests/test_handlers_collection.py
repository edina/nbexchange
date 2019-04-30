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


##### POST /collection #####

# No method available (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_collection0(app):
    r = yield async_requests.post(app.url + "/collection")
    assert r.status_code == 501


# subscribed user makes no difference (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_assignments1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + "/collection?course_id=course_2")
    assert r.status_code == 501


##### GET /collection (download/collect student submissions) #####

# require authenticated user
@pytest.mark.gen_test
def test_collection0(app):
    r = yield async_requests.get(app.url + "/collection")
    assert r.status_code == 403


# Requires three params (none)
@pytest.mark.gen_test
def test_collection1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/collection")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Collection call requires a course code, an assignment code, and a path"
    )


# Requires three params (given course & assignment)
@pytest.mark.gen_test
@pytest.mark.skip
def test_collection2(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  ## Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        r = yield async_requests.get(
            app.url
            + f"/collection?course_id={collected_data['course_id']}&assignment_id={collected_data['assignment_id']}"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Collection call requires a course code, an assignment code, and a path"
    )


# # Requires three params (given course & path)
# @pytest.mark.gen_test
# def test_collection3(app):
#     with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
#             collected_data = None
#             r = yield async_requests.get(
#                 app.url + "/collections?course_id=course_2&assignment_id=assign_a"
#             )  ## Get the data we need to make test the call we want to make
#             response_data = r.json()
#             collected_data = response_data["value"][0]
#             r = yield async_requests.get(
#                 app.url
#                 + f"/collection?course_id={collected_data['course_id']}&path={collected_data['path']}"
#             )
#     assert r.status_code == 200
#     response_data = r.json()
#     assert response_data["success"] == False
#     assert (
#         response_data["note"]
#         == "Collection call requires a course code, an assignment code, and a path"
#     )


# # Requires three params (given assignment & path)
# @pytest.mark.gen_test
# def test_collection4(app):
#     with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
#             collected_data = None
#             r = yield async_requests.get(
#                 app.url + "/collections?course_id=course_2&assignment_id=assign_a"
#             )  ## Get the data we need to make test the call we want to make
#             response_data = r.json()
#             collected_data = response_data["value"][0]
#             r = yield async_requests.get(
#                 app.url
#                 + f"/collection?path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"
#             )
#     assert r.status_code == 200
#     response_data = r.json()
#     assert response_data["success"] == False
#     assert (
#         response_data["note"]
#         == "Collection call requires a course code, an assignment code, and a path"
#     )


# # Has all three params, not subscribed to course
# @pytest.mark.gen_test
# def test_collection5(app):
#     with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
#             collected_data = None
#             r = yield async_requests.get(
#                 app.url + "/collections?course_id=course_2&assignment_id=assign_a"
#             )  ## Get the data we need to make test the call we want to make
#             response_data = r.json()
#             collected_data = response_data["value"][0]
#             r = yield async_requests.get(
#                 app.url
#                 + f"/collection?course_id=course_1&path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"
#             )
#     assert r.status_code == 200
#     response_data = r.json()
#     assert response_data["success"] == False
#     assert response_data["note"] == "User not subscribed to course course_1"


# Has all three params, student can't collect (note this is hard-coded params, as students can list items available for collection)
@pytest.mark.gen_test
def test_collection6(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.get(
            app.url
            + f"/collection?course_id=course_2&path=/foo/car/file.gz&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == f"User not an instructor to course course_2"


# # Has all three params, instructor can collect
# @pytest.mark.gen_test
# def test_collection7(app):
#     with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
#             collected_data = None
#             r = yield async_requests.get(
#                 app.url + "/collections?course_id=course_2&assignment_id=assign_a"
#             )  ## Get the data we need to make test the call we want to make
#             response_data = r.json()
#             collected_data = response_data["value"][0]
#             r = yield async_requests.get(
#                 app.url
#                 + f"/collection?course_id={collected_data['course_id']}&path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"
#             )
#     assert r.status_code == 200
#     assert r.headers["Content-Type"] == "application/gzip"
#     assert int(r.headers["Content-Length"]) > 0
