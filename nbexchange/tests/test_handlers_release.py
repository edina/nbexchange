import logging
import shutil

import pytest
from mock import patch
from tornado import web

from nbexchange.handlers.assignment import Assignment
from nbexchange.handlers.base import BaseHandler
from nbexchange.tests.utils import (  # noqa: F401 "clear_database"
    async_requests,
    clear_database,
    create_any_tarball,
    get_files_dict,
    user_kiz,
    user_kiz_instructor,
    user_kiz_student,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

# set up the file to be uploaded
release_files, notebooks, timestamp = get_files_dict()  # ourself :)

# #### POST /assignment (upload/release assignment) ##### #


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
# Note you also want to clear the exchange filestore too.... again, so files from 1 test don't throw another test
#
#################################


# require authenticated user (404 because the bounce to login fails)
@pytest.mark.gen_test
def test_post_requires_authenticated_user(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value={}):
        r = yield async_requests.post(app.url + "/assignment")
    assert r.status_code == 403  # why not 404???


# Requires both params (none)
@pytest.mark.gen_test
def test_post_no_params(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/assignment")
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Posting an Assigment requires a course code and an assignment code"


# Requires both params (just course)
@pytest.mark.gen_test
def test_post_missing_assignment(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/assignment?course_id=course_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Posting an Assigment requires a course code and an assignment code"


# Requires both params (just assignment)
@pytest.mark.gen_test
def test_post_missing_course(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/assignment?assignment_id=assign_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Posting an Assigment requires a course code and an assignment code"


# Student cannot release
@pytest.mark.gen_test
def test_post_student_cannot_release(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "User not an instructor to course course_2"


# instructor can release
@pytest.mark.gen_test
def test_post_release_ok(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            data={"notebooks": notebooks},
            files=release_files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert response_data["note"] == "Released"


@pytest.mark.gen_test
def test_post_release_broken_nbex_user(app, clear_database, caplog):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    assert r.status_code == 500
    assert "Both current_course ('None') and current_role ('None') must have values. User was '1-kiz'" in caplog.text


# fails if no file is part of post request
@pytest.mark.gen_test
def test_post_no_file_provided(app, clear_database, caplog):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    assert r.status_code == 412
    assert "assignment handler upload: No file supplied in upload" in caplog.text


# Instructor, wrong course, cannot release
@pytest.mark.gen_test
def test_post_wrong_course(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/assignment?course_id=course_1&assignment_id=assign_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "User not subscribed to course course_1"


# instructor releasing - Picks up the first attribute if more than 1 (wrong course)
@pytest.mark.gen_test
def test_post_picks_first_instance_of_param_gets_it_wrong(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_1&course_id=course_2&assignment_id=assign_a",
            data={"notebooks": notebooks},
            files=release_files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "User not subscribed to course course_1"


# instructor releasing - Picks up the first attribute if more than 1 (right course)
@pytest.mark.gen_test
def test_post_picks_first_instance_of_param_gets_it_right(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&course_id=course_1&assignment_id=assign_a",
            data={"notebooks": notebooks},
            files=release_files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert response_data["note"] == "Released"
    shutil.rmtree(app.base_storage_location)


# Confirm 3 releases lists 3 actions, with 3 different locations
# @pytest.mark.skip
@pytest.mark.gen_test
def test_post_location_different_each_time(app, clear_database):  # noqa: F811
    data = {"notebooks": notebooks}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            data=data,
            files=release_files,
        )
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            # data=data,
            files=release_files,
        )
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            # data={"notebooks": notebooks},
            files=release_files,
        )
        r = yield async_requests.get(app.url + "/assignments?course_id=course_2")
    assert r.status_code == 200
    response_data = r.json()

    assert response_data["success"] is True
    assert "note" not in response_data  # just that it's missing
    paths = list(map(lambda assignment: assignment["path"], response_data["value"]))
    actions = list(map(lambda assignment: assignment["status"], response_data["value"]))
    assert len(paths) == 3

    assert paths[0] != paths[1]  # 1st relase is not the same path as the 2nd release
    assert paths[1] != paths[2]  # 2nd not the same as 3rd
    assert paths[0] != paths[2]  # 1st not the same as third
    assert actions == ["released", "released", "released"]
    shutil.rmtree(app.base_storage_location)


@pytest.mark.gen_test
def test_105MB_not_blocked(app, clear_database):  # noqa: F811
    faked_tarball = create_any_tarball(104857600)  # 105MB
    faked_files = {"assignment": ("assignment.tar.gz", faked_tarball)}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            data={"notebooks": notebooks},
            files=faked_files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert response_data["note"] == "Released"
    shutil.rmtree(app.base_storage_location)


# Note, the web HTTPServer just throws a 400 error for an oversized file
# There is no way to catch/handle that _server side_
@pytest.mark.skip
@pytest.mark.gen_test
def test_5point1GB_is_blocked__long_test(app, clear_database):  # noqa: F811
    faked_tarball = create_any_tarball(5476083302)  # 5.1GB
    faked_files = {"assignment": ("assignment.tar.gz", faked_tarball)}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            data={"notebooks": notebooks},
            files=faked_files,
        )
    assert r.status_code == 400
    assert r.content == b""


# fakes something going wrong in the "write to disk" code
@pytest.mark.gen_test
def test_post_file_save_error(app, clear_database, caplog):  # noqa: F811
    with patch.object(Assignment, "post", side_effect=web.HTTPError(500, "Upload failed: foo")):
        r = yield async_requests.post(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    assert r.status_code == 500
    assert "Upload failed: foo" in caplog.text
