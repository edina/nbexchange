import json
import logging
import sys
import pytest
import re
import requests

from bs4 import BeautifulSoup
from mock import MagicMock, patch

from nbexchange.app import NbExchange
from nbexchange.base import BaseHandler
from nbexchange.tests.utils import async_requests, tar_source
from nbexchange.handlers.assignment import Assignments, Assignment
from nbexchange.handlers.submission import Submissions, Submission
from nbexchange.handlers.collection import Collections, Collection
from time import sleep
from urllib.parse import urlparse

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

user_kiz_instructor = {
    "name": "1_kiz",
    "course_id": "course_2",
    "course_role": "Instructor",
    "course_title": "A title",
}
user_kiz_student = {
    "name": "1_kiz",
    "course_id": "course_2",
    "course_role": "Student",
    "course_title": "A title",
}
user_brobbere_instructor = {
    "name": "1_brobbere",
    "course_id": "course_2",
    "course_role": "Instructor",
    "course_title": "A title",
}
user_brobbere_student = {
    "name": "1_brobbere",
    "course_id": "course_2",
    "course_role": "Student",
}


##### basic  #####
# Test that the base endpoint returns a text string (ie the end-point is alive)
@pytest.mark.gen_test
@pytest.mark.remote
def test_main_page(app):
    """Check the main page"""
    r = yield async_requests.get(app.url + "/")
    assert r.status_code == 200
    assert re.search(r"NbExchange", r.text)


##### GET /assignments (list assignments)######

# require authenticated user (404 because the bounce to login fails)
@pytest.mark.gen_test
def test_assignments0(app):
    r = yield async_requests.get(app.url + "/assignments")
    assert r.status_code == 401


# Requires a course_id param
@pytest.mark.gen_test
def test_assignments1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/assignments")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Assigment call requires a course id"


# test when not subscribed
@pytest.mark.gen_test
def test_assignments2(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/assignments?course_id=course_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "User not subscribed to course course_a"


# test when subscribed
@pytest.mark.gen_test
def test_assignments3(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/assignments?course_id=course_2")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == True
    assert "note" not in response_data  # just that it's missing
    assert "value" in response_data  # just that it's present (it will have no content)


##### POST /assignments  ######
# No method available (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_assignments0(app):
    r = yield async_requests.post(app.url + "/assignments")
    assert r.status_code == 501


# subscribed user makes no difference (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_assignments1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + "/assignments?course_id=course_2")
    assert r.status_code == 501


##### GET /assignment (download/fetch assignment)  ######

# require authenticated user (404 because the bounce to login fails)
@pytest.mark.gen_test
@pytest.mark.skip
def test_assignment0(app):
    r = yield async_requests.get(app.url + "/assignment")
    assert r.status_code == 401


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
            app.url + "/assignment?course_id=course_2&assignment_id=weird_assignment"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Assignment weird_assignment does not exist"


# both params, correct course, assignment does not exist - differnet user, same role
@pytest.mark.gen_test
def test_assignment6(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_instructor
    ):
        r = yield async_requests.get(
            app.url
            + "/assignment?course_id=course_2&assignment_id=this_assignment_is_not_here"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"] == "Assignment this_assignment_is_not_here does not exist"
    )


# both params, correct course, assignment does not exist - same user, different role
@pytest.mark.gen_test
def test_assignment7(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):

        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=test_assignment_7"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Assignment test_assignment_7 does not exist"


# both params, correct course, assignment does not exist - different user, different role
@pytest.mark.gen_test
def test_assignment8(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):

        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=test_assignment8"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Assignment test_assignment8 does not exist"


# additional param makes no difference
@pytest.mark.gen_test
def test_assignment9(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):

        r = yield async_requests.get(
            app.url
            + "/assignment?course_id=course_2&assignment_id=test_assignment9&foo=bar"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Assignment test_assignment9 does not exist"


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
            + "/assignment?course_id=course_2&course_id=cource_a&assignment_id=test_assignment11"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Assignment test_assignment11 does not exist"


# !! test_assignment12-> after release tests !!

##### POST /assignment (upload/release assignment) ######

# require authenticated user
@pytest.mark.gen_test
@pytest.mark.skip
def test_post_assignment0(app):
    r = yield async_requests.post(app.url + "/assignment")
    assert r.status_code == 401


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


##### fetch assignment (download) now upload has happened ######
# fetch assignment, correct course, assignment does not exist
@pytest.mark.gen_test
def test_assignment12(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_b"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Assignment assign_b does not exist"


# fetch assignment, correct details, same user as releaser
@pytest.mark.gen_test
def test_assignment13(app):
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
@pytest.mark.gen_test
def test_assignment14(app):
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


# fetch assignment, correct details, different user, different role
@pytest.mark.gen_test
def test_assignment16(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):

        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&course_1&assignment_id=assign_a"
        )
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "application/gzip"
    assert int(r.headers["Content-Length"]) > 0


##### POST /submissions ######
# No method available (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_assignments0(app):
    r = yield async_requests.post(app.url + "/submissions")
    assert r.status_code == 501


# subscribed user makes no difference (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_assignments1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
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
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/submissions?course_id=course_2")
    assert r.status_code == 501


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

# require authenticated user (401 because the bounce to login fails)
@pytest.mark.gen_test
@pytest.mark.skip
def test_post_assignments0(app):
    r = yield async_requests.post(app.url + "/submission")
    assert r.status_code == 401


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


# Student can submit
@pytest.mark.gen_test
def test_post_submision4(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == True
    assert response_data["note"] == "Submitted"


# instructor can submit
@pytest.mark.gen_test
def test_post_submision5(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == True
    assert response_data["note"] == "Submitted"


# fails if no file is part of post request
@pytest.mark.gen_test
def test_post_submision4(app):
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a"
        )
    assert r.status_code == 412


# Picks up the first attribute if more than 1 (wrong course)
@pytest.mark.gen_test
def test_post_submision4(app):
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_1&course_2&assignment_id=assign_a",
            files=files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Submitted"


# Picks up the first attribute if more than 1 (right course)
@pytest.mark.gen_test
def test_post_submision4(app):
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == True
    assert response_data["note"] == "Submitted"


##### GET /collections (list available assignments for collection) #####

# require authenticated user (401 because the bounce to login fails)
@pytest.mark.gen_test
@pytest.mark.skip
def test_collections0(app):
    r = yield async_requests.get(app.url + "/collections")
    assert r.status_code == 401


# Requires both params (none)
@pytest.mark.gen_test
def test_collections1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/collections")
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Collections call requires both a course code and an assignment code"
    )


# Requires both params (just course)
@pytest.mark.gen_test
def test_collections2(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/collections?course_id=course_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Collections call requires both a course code and an assignment code"
    )


# Requires both params (just assignment)
@pytest.mark.gen_test
def test_collections3(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/collections?assignment_id=assign_a")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Collections call requires both a course code and an assignment code"
    )


# both params, incorrect course
@pytest.mark.gen_test
def test_collections4(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_1&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "User not subscribed to course course_1"


# both params, correct course, assignment does not exist
# returns true, but empty
@pytest.mark.gen_test
def test_collections5(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_b2"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == True
    assert "note" not in response_data  # just that it's missing
    assert "value" in response_data  # just that it's present (it will have no content)


# both params, correct details
@pytest.mark.gen_test
def test_collections6(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == True
    assert "note" not in response_data  # just that it's missing
    assert "value" in response_data  # just that it's present (it will have no content)


# both params, correct course, assignment does not exist - differnet user, same role
# Passes, because instructor on course
@pytest.mark.gen_test
def test_collections7(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_instructor
    ):
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == True
    assert "note" not in response_data  # just that it's missing
    assert "value" in response_data  # just that it's present (it will have no content)


# student cannot collect
@pytest.mark.gen_test
def test_collections8(app):
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "User not an instructor to course course_2"


# Picks up the first attribute if more than 1 (wrong course)
@pytest.mark.gen_test
def test_collections9(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_instructor
    ):
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_1&course_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "User not subscribed to course course_1"


# Picks up the first attribute if more than 1 (right course)
@pytest.mark.gen_test
def test_collections10(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_instructor
    ):
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&course_1&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == True
    assert "note" not in response_data  # just that it's missing
    assert "value" in response_data  # just that it's present (it will have no content)


##### POST /collections #####
# No method available (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_collections0(app):
    r = yield async_requests.post(app.url + "/collections")
    assert r.status_code == 501


# subscribed user makes no difference (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_assignments1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + "/collections?course_id=course_2")
    assert r.status_code == 501


##### GET /collection (download/collect student submissions) #####

# require authenticated user
@pytest.mark.gen_test
@pytest.mark.skip
def test_collection0(app):
    r = yield async_requests.get(app.url + "/collection")
    assert r.status_code == 401


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


# Requires three params (given course & path)
@pytest.mark.gen_test
def test_collection3(app):
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
            + f"/collection?course_id={collected_data['course_id']}&path={collected_data['path']}"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Collection call requires a course code, an assignment code, and a path"
    )


# Requires three params (given assignment & path)
@pytest.mark.gen_test
def test_collection4(app):
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
            + f"/collection?path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Collection call requires a course code, an assignment code, and a path"
    )


# Has all three params, not subscribed to course
@pytest.mark.gen_test
def test_collection5(app):
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
            + f"/collection?course_id=course_1&path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "User not subscribed to course course_1"


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


# Has all three params, instructor can collect
@pytest.mark.gen_test
def test_collection7(app):
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
            + f"/collection?course_id={collected_data['course_id']}&path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"
        )
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "application/gzip"
    assert int(r.headers["Content-Length"]) > 0


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
