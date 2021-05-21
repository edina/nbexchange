import logging
import sys

import pytest
from mock import patch

from nbexchange.handlers.base import BaseHandler
from nbexchange.tests.utils import (
    async_requests,
    clear_database,
    get_files_dict,
    user_kiz_instructor,
    user_kiz_student,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

##### POST /assignment (upload/release assignment) ######

# require authenticated user (404 because the bounce to login fails)
@pytest.mark.gen_test
def test_post_assignment0(app):
    with patch.object(BaseHandler, "get_current_user", return_value={}):
        r = yield async_requests.post(app.url + "/assignment")
    assert r.status_code == 403  # why not 404???


# set up the file to be uploaded
files = get_files_dict(sys.argv[0])  # ourself :)

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


# instructor can release
@pytest.mark.gen_test
def test_post_assignment5(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == True
    assert response_data["note"] == "Released"


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


# instructor releasing - Picks up the first attribute if more than 1 (right course)
@pytest.mark.gen_test
def test_post_assignment9(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + "/assignment?course_id=course_2&course_id=course_1&assignment_id=assign_a",
            files=files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == True
    assert response_data["note"] == "Released"


# Confirm 3 releases lists 3 actions, with 3 different locations
@pytest.mark.skip
@pytest.mark.gen_test
def test_post_assignment10(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
        r = yield async_requests.get(app.url + "/assignments?course_id=course_2")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == True
    assert "note" not in response_data  # just that it's missing
    paths = list(map(lambda assignment: assignment["path"], response_data["value"]))
    actions = list(map(lambda assignment: assignment["status"], response_data["value"]))
    assert len(paths) == 3

    assert paths[0] != paths[1]  # 1st relase is not the same path as the 2nd release
    assert paths[1] != paths[2]  # 2nd not the same as 3rd
    assert paths[0] != paths[2]  # 1st not the same as third
    assert actions == ["released", "released", "released"]


@pytest.mark.gen_test
def test_blocks_filesize(app, clear_database):
    with patch.object(BaseHandler, "max_buffer_size", return_value=int(50)):
        with patch.object(
            BaseHandler, "get_current_user", return_value=user_kiz_instructor
        ):
            r = yield async_requests.post(
                app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
                files=files,
            )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "File upload oversize, and rejected. Please reduce the contents of the assignment, re-generate, and re-release"
    )
