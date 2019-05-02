import json
import logging
import pytest
import re
import requests
import sys
import time

from mock import patch
from nbexchange.app import NbExchange
from nbexchange.base import BaseHandler
from nbexchange.tests.utils import (
    async_requests,
    get_files_dict,
    user_kiz_instructor,
    user_brobbere_instructor,
    user_kiz_student,
    user_brobbere_student,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

# set up the file to be uploaded as part of the testing later
files = get_files_dict(sys.argv[0])  # ourself :)

##### GET /assignment (download/fetch assignment)  ######

# require authenticated user (404 because the bounce to login fails)
@pytest.mark.gen_test
def test_assignment0(app):
    r = yield async_requests.get(app.url + "/assignment")
    assert r.status_code == 403


# Requires both params (none)
@pytest.mark.gen_test
def test_assignment1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/assignment")
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Assigment call requires both a course code and an assignment code!!"
    )


# Requires both params (just course)
@pytest.mark.gen_test
def test_assignment2(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Assigment call requires both a course code and an assignment code!!"
    )


# Requires both params (just assignment)
@pytest.mark.gen_test
def test_assignment3(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/assignment?assignment_id=assign_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Assigment call requires both a course code and an assignment code!!"
    )


# both params, incorrect course
@pytest.mark.gen_test
def test_assignment4(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_1&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "User not subscribed to course course_1"


# both params, correct course, assignment does not exist
@pytest.mark.gen_test
def test_assignment5(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Assignment assign_a does not exist"


# both params, correct course, assignment does not exist - differnet user, same role
@pytest.mark.gen_test
def test_assignment6(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_instructor
    ):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Assignment assign_a does not exist"


# both params, correct course, assignment does not exist - same user, different role
@pytest.mark.gen_test
def test_assignment7(app):
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Assignment assign_a does not exist"


# both params, correct course, assignment does not exist - different user, different role
@pytest.mark.gen_test
def test_assignment8(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Assignment assign_a does not exist"


# additional param makes no difference
@pytest.mark.gen_test
def test_assignment9(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a&foo=bar"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Assignment assign_a does not exist"


# Picks up the first attribute if more than 1 (wrong course)
@pytest.mark.gen_test
def test_assignment10(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.get(
            app.url
            + "/assignment?course_id=course_a&course_id=cource_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "User not subscribed to course course_a"


# Picks up the first attribute if more than 1 (right course)
@pytest.mark.gen_test
def test_assignment11(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.get(
            app.url
            + "/assignment?course_id=course_2&course_id=cource_a&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Assignment assign_a does not exist"


# fetch assignment, correct details, same user as releaser
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_assignment13(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "application/gzip"
    assert int(r.headers["Content-Length"]) > 0


# fetch assignment, correct details, different user, different role
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_assignment14(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "application/gzip"
    assert int(r.headers["Content-Length"]) > 0


# fetch assignment, correct details, different user, different role - Picks up the first attribute if more than 1 (wrong course)
@pytest.mark.gen_test
def test_assignment15(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.get(
            app.url
            + "/assignment?course_id=course_1&course_id=course_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "User not subscribed to course course_1"


# Confirm that a fetch always matches the last release
@pytest.mark.gen_test
def test_post_assignment9(app):
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
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.get(
            app.url + "/assignment?&course_id=course_2&assignment_id=assign_a"
        )
        r = yield async_requests.get(app.url + "/assignments?course_id=course_2")
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.get(
            app.url + "/assignment?&course_id=course_2&assignment_id=assign_a"
        )
        r = yield async_requests.get(app.url + "/assignments?course_id=course_2")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == True
    assert "note" not in response_data  # just that it's missing
    paths = list(map(lambda assignment: assignment["path"], response_data["value"]))
    actions = list(map(lambda assignment: assignment["status"], response_data["value"]))
    print(f"returned assignments list: {response_data['value']}")
    print(f"fetch paths: {paths}")
    print(f"fetch actions: {actions}")
    assert len(paths) == 6
    assert actions == [
        "released",
        "released",
        "released",
        "fetched",
        "released",
        "fetched",
    ]
    assert paths[2] == paths[3]  # First fetch = third release
    assert paths[4] == paths[5]  # Second fetch = fourth release
    assert paths[3] != paths[5]  # First fetch is not the same as the second fetch
