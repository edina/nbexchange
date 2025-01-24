import logging

import pytest
from mock import patch

from nbexchange.handlers.base import BaseHandler
from nbexchange.tests.utils import (  # noqa: F401 "clear_database"
    async_requests,
    clear_database,
    get_files_dict,
    user_kiz,
    user_kiz_instructor,
    user_kiz_student,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

# set up the file to be uploaded as part of the testing later
release_files, notebooks, timestamp = get_files_dict()


# #### GET /submission ##### #
# No method available (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_get_submission_is_501(app):
    r = yield async_requests.get(app.url + "/submission")
    assert r.status_code == 501


# subscribed user makes no difference (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_get_submission_501_even_authenticated(app):
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/submission?course_id=course_2")
    assert r.status_code == 501


# #### POST /submission (submit assignment) ##### #


# require authenticated user
@pytest.mark.gen_test
def test_post_403_if_not_authenticated(app):
    with patch.object(BaseHandler, "get_current_user", return_value={}):
        r = yield async_requests.post(app.url + "/submission")
    assert r.status_code == 403


# Requires both params (none)
@pytest.mark.gen_test
def test_post_submision_requires_two_params(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/submission")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Submission call requires both a course code and an assignment code"


# Requires both params (just course)
@pytest.mark.gen_test
def test_post_submision_needs_assignment(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/submission?course_id=course_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Submission call requires both a course code and an assignment code"


# Requires both params (just assignment)
@pytest.mark.gen_test
def test_post_submision_needs_course(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/submission?assignment_id=assign_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Submission call requires both a course code and an assignment code"


# User not fetched assignment
@pytest.mark.gen_test
def test_post_submision_checks_subscription(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(app.url + "/submission?course_id=course_2&assignment_id=assign_c")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "User not fetched assignment assign_c"


# Student can submit
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_post_submision_student_can_submit(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert response_data["note"] == "Submitted"


# broken nbex_user throws a 500 error on the server
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_post_submision_broken_nbex_user(app, clear_database, caplog):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    assert r.status_code == 500
    assert "Both current_course ('None') and current_role ('None') must have values. User was '1-kiz'" in caplog.text


# instructor can submit
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_post_submision_instructor_can_submit(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert response_data["note"] == "Submitted"


# fails if no file is part of post request
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_post_submision_requires_files(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(app.url + "/submission?course_id=course_2&assignment_id=assign_a")
    assert r.status_code == 412


# Picks up the first attribute if more than 1 (wrong course)
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_post_submision_picks_first_instance_of_param_a(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_1&course_2&assignment_id=assign_a",
            files=release_files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "User not subscribed to course course_1"


# Picks up the first attribute if more than 1 (right course)
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_post_submision_piks_first_instance_of_param_b(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert response_data["note"] == "Submitted"


@pytest.mark.gen_test
def test_post_submision_oversize_blocked(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "max_buffer_size", return_value=int(50)):
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            r = yield async_requests.post(
                app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
                files=release_files,
            )
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            r = yield async_requests.post(
                app.url + "/submission?course_id=course_2&assignment_id=assign_a",
                files=release_files,
            )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "File upload oversize, and rejected. Please reduce the files in your submission and try again."  # noqa: E501 W503
    )
