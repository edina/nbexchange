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


##### GET /collections (list available assignments for collection) #####

# require authenticated user
@pytest.mark.gen_test
def test_collections0(app):
    r = yield async_requests.get(app.url + "/collections")
    assert r.status_code == 403


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
@pytest.mark.skip
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
@pytest.mark.skip
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
@pytest.mark.skip
def test_collections7(app):
    with patch.object(BaseHandler, "get_current_user", return_value=user_bert):
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
