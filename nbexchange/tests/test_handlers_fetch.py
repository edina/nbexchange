import logging
import sys

import pytest
from mock import patch

from nbexchange.handlers.base import BaseHandler
from nbexchange.tests.utils import (  # noqa: F401 "clear_database"
    async_requests,
    clear_database,
    get_files_dict,
    user_brobbere_student,
    user_kiz,
    user_kiz_instructor,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

# set up the file to be uploaded as part of the testing later
files = get_files_dict(sys.argv[0])  # ourself :)

#################################
#
# Very Important Note
#
# The `clear_database` fixture removed all database records.
# In this suite of tests, we do that FOR EVERY TEST
# This means that every single test is run in isolation, and therefore will need to have the full Release, Fetch,
#   Submit steps done before the collection can be tested.
# (On the plus side, adding or changing a test will no longer affect those below)
#
#################################


# #### GET /assignment (download/fetch assignment)  ##### #

# require authenticated user (404 because the bounce to login fails)
@pytest.mark.gen_test
def test_fetch_requires_auth_user(app):
    r = yield async_requests.get(app.url + "/assignment")
    assert r.status_code == 403


# Requires both params (none)
@pytest.mark.gen_test
def test_fetch_fails_no_parama(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/assignment")
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Assigment call requires both a course code and an assignment code!!"


# Requires both params (just course)
@pytest.mark.gen_test
def test_fetch_fails_missing_assignment(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Assigment call requires both a course code and an assignment code!!"


# Requires both params (just assignment)
@pytest.mark.gen_test
def test_fetch_fails_missing_course(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/assignment?assignment_id=assign_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Assigment call requires both a course code and an assignment code!!"


# both params, incorrect course
@pytest.mark.gen_test
def test_fetch_fails_user_not_subscribed(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_1&assignment_id=assign_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "User not subscribed to course course_1"


# both params, correct course, assignment does not exist
@pytest.mark.gen_test
def test_fetch_fails_assignment_not_exists(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_does_not_exist")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Assignment assign_does_not_exist does not exist"


# Picks up the first attribute if more than 1 (wrong course)
@pytest.mark.gen_test
def test_fetch_duplicate_param_first_is_wrong(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_brobbere_student):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_a&course_id=cource_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "User not subscribed to course course_a"


# Picks up the first attribute if more than 1 (right course)
@pytest.mark.gen_test
def test_fetch_duplicate_param_first_is_right(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_brobbere_student):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&course_id=cource_a&assignment_id=assign_does_not_exist"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Assignment assign_does_not_exist does not exist"


# fetch assignment, correct details, same user as releaser
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_instructor_can_fetch(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/assignment?course_id=course_2&assignment_id=assign_a", files=files)
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "application/gzip"
    assert int(r.headers["Content-Length"]) > 0


# broken nbex_user throws a 500 error on the server
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_fetch_broken_nbex_user(app, clear_database, caplog):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/assignment?course_id=course_2&assignment_id=assign_a", files=files)
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
        assert r.status_code == 500
        assert (
            "Both current_course ('None') and current_role ('None') must have values. User was '1-kiz'" in caplog.text
        )


# fetch assignment, correct details, different user, different role
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_student_can_fetch(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/assignment?course_id=course_2&assignment_id=assign_a", files=files)
    with patch.object(BaseHandler, "get_current_user", return_value=user_brobbere_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "application/gzip"
    assert int(r.headers["Content-Length"]) > 0


# Confirm that a fetch always matches the last release
@pytest.mark.gen_test
def test_fetch_after_rerelease_gets_different_file(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/assignment?course_id=course_2&assignment_id=assign_a", files=files)
        r = yield async_requests.post(app.url + "/assignment?course_id=course_2&assignment_id=assign_a", files=files)
        r = yield async_requests.post(app.url + "/assignment?course_id=course_2&assignment_id=assign_a", files=files)
    with patch.object(BaseHandler, "get_current_user", return_value=user_brobbere_student):
        r = yield async_requests.get(app.url + "/assignment?&course_id=course_2&assignment_id=assign_a")
        r = yield async_requests.get(app.url + "/assignments?course_id=course_2")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/assignment?course_id=course_2&assignment_id=assign_a", files=files)
    with patch.object(BaseHandler, "get_current_user", return_value=user_brobbere_student):
        r = yield async_requests.get(app.url + "/assignment?&course_id=course_2&assignment_id=assign_a")
        r = yield async_requests.get(app.url + "/assignments?course_id=course_2")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert "note" not in response_data  # just that it's missing
    paths = list(map(lambda assignment: assignment["path"], response_data["value"]))
    actions = list(map(lambda assignment: assignment["status"], response_data["value"]))
    assert len(paths) == 6
    assert actions == ["released", "released", "released", "fetched", "released", "fetched"]
    assert paths[2] == paths[3]  # First fetch = third release
    assert paths[4] == paths[5]  # Second fetch = fourth release
    assert paths[3] != paths[5]  # First fetch is not the same as the second fetch
