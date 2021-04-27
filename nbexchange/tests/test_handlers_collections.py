import logging
import sys

import pytest
from mock import patch

from nbexchange.handlers.base import BaseHandler
from nbexchange.tests.utils import (
    async_requests,
    clear_database,
    get_files_dict,
    user_brobbere_instructor,
    user_brobbere_student,
    user_kiz_instructor,
    user_kiz_student,
    user_zik_student,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

# set up the file to be uploaded as part of the testing later
files = get_files_dict(sys.argv[0])  # ourself :)

##### POST /collections #####
# No method available (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_collections_no_post_action(app):
    r = yield async_requests.post(app.url + "/collections")
    assert r.status_code == 501


# subscribed user makes no difference (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_collections_no_post_action_even_authenticated(app, clear_database):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + "/collections?course_id=course_2")
    assert r.status_code == 501


##### GET /collections (list available assignments for collection) #####

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

# require authenticated user
@pytest.mark.gen_test
def test_collections_unauthenticated_user_blocked(app, clear_database):
    r = yield async_requests.get(app.url + "/collections")
    assert r.status_code == 403


# Requires both params (none)
@pytest.mark.gen_test
def test_collections_fails_with_no_parameters(app, clear_database):
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
def test_collections_fails_with_just_course_parameter(app, clear_database):
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
def test_collections_fails_with_just_assignment_parameter(app, clear_database):
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
def test_collections_fails_with_wrong_course_code(app, clear_database):
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
def test_collections_zero_results_with_wrong_course(app, clear_database):

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
    assert response_data["value"] == []  # it will have no content


# both params, correct details
# (needs to be submitted before it can be seen )
@pytest.mark.gen_test
def test_collections_zero_results_if_no_submissions(app, clear_database):
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
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == True
    assert "note" not in response_data  # just that it's missing
    assert response_data["value"] == []


# both params, correct course, assignment does not exist - differnet user, same role
# Passes, because instructor on course
@pytest.mark.gen_test
def test_collections_zero_results_instructor_autosubscribed_to_course(
    app, clear_database
):
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
    assert response_data["value"] == []


# student cannot collect
@pytest.mark.gen_test
def test_collections_students_cannot_collect(app, clear_database):
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
def test_collections_repeated_parameters_wrong_first(app, clear_database):
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
def test_collections_repeated_parameters_right_first(app, clear_database):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )  ## Release
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_instructor
    ):
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&course_1&assignment_id=assign_a"
        )  ## Collect
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == True
    assert "note" not in response_data  # just that it's missing
    assert response_data["value"] == []


@pytest.mark.gen_test
def test_collections_with_two_users_submitting(app, clear_database):
    assignment_id_1 = "assign_a"
    assignment_id_2 = "b_assign"
    course_id = "course_2"
    notebook = "notebook"

    # XXX: Doing this in a separate function doesn't work for some reason
    #  (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
            **kwargs,
        )  ## Release
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id_2}",
            files=files,
            **kwargs,
        )  ## Release 2nd assignment
    # Submissions check for a released action, not a fetched one
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
        )  ## submit
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
        )  ## submit 2nd user
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(
            app.url
            + f"/collections?course_id={course_id}&assignment_id={assignment_id_1}"
        )  ## collect

    response_data = r.json()
    assert response_data["success"] is True
    assert len(response_data["value"]) == 2


@pytest.mark.gen_test
def test_collections_with_one_user_submits_2nd_time(app, clear_database):
    assignment_id_1 = "assign_a"
    course_id = "course_2"
    notebook = "notebook"

    # XXX: Doing this in a separate function doesn't work for some reason
    #  (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
            **kwargs,
        )  ## Released
    # Submissions check for a released action, not a fetched one
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
        )  ## Submitted
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
        )  ## Submitted 2nd time
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(
            app.url
            + f"/collections?course_id={course_id}&assignment_id={assignment_id_1}"
        )  ## Collected
    response_data = r.json()
    assert response_data["success"] is True
    assert len(response_data["value"]) == 2


@pytest.mark.gen_test
def test_collections_with_named_user(app, clear_database):
    assignment_id_1 = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = "1-kiz"

    # XXX: Doing this in a separate function doesn't work for some reason
    #  (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
            **kwargs,
        )  ## Released
    # Submissions check for a released action, not a fetched one
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
        )  ## Submitted
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
        )  ## Submitted 2nd user
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(
            app.url
            + f"/collections?course_id={course_id}&assignment_id={assignment_id_1}&user_id={student}"
        )  ## collected

    response_data = r.json()
    assert response_data["success"] is True
    assert len(response_data["value"]) == 1


@pytest.mark.gen_test
def test_collections_with_named_user_check_full_name(app, clear_database):
    assignment_id_1 = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = "1-zik"

    # XXX: Doing this in a separate function doesn't work for some reason
    #  (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
            **kwargs,
        )  ## Released
    # Submissions check for a released action, not a fetched one
    with patch.object(BaseHandler, "get_current_user", return_value=user_zik_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
        )

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(
            app.url
            + f"/collections?course_id={course_id}&assignment_id={assignment_id_1}&user_id={student}"
        )

    response_data = r.json()
    assert response_data["success"] is True
    assert len(response_data["value"]) == 1
    for value in response_data["value"]:
        assert value["full_name"] == "One Zik"


@pytest.mark.gen_test
def test_collections_with_named_user_check_full_name_missing(app, clear_database):
    assignment_id_1 = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = "1-brobbere"

    # XXX: Doing this in a separate function doesn't work for some reason
    #  (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
            **kwargs,
        )  ## Released
    # Submissions check for a released action, not a fetched one
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
        )

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(
            app.url
            + f"/collections?course_id={course_id}&assignment_id={assignment_id_1}&user_id={student}"
        )

    response_data = r.json()
    assert response_data["success"] is True
    # 2 if run solo, 8 is run in the complete suite
    assert len(response_data["value"]) == 1
    for value in response_data["value"]:
        assert value["full_name"] is None


# Reminder: actions are persistent, so the previous test set up most of the actions
@pytest.mark.gen_test
def test_collections_with_a_blank_feedback_path_injected(app, clear_database):
    assignment_id_1 = "assign_a"
    course_id = "course_2"
    notebook = "notebook"

    # XXX: Doing this in a separate function doesn't work for some reason
    #  (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
            **kwargs,
        )  ## Released
    # Submissions check for a released action, not a fetched one
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
        )  ## Submitted
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
        )  ## Submitted 2nd time
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id_1}",
            files=files,
        )  ## Submitted 2nd user

    # Now manually inject a `feedback_fetched` action
    import nbexchange.models.actions
    from nbexchange.database import scoped_session

    with scoped_session() as session:

        action = nbexchange.models.actions.Action(
            user_id=3,
            assignment_id=1,
            action=nbexchange.models.actions.AssignmentActions.feedback_fetched.value,
            location=None,
        )
        session.add(action)

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(
            app.url
            + f"/collections?course_id={course_id}&assignment_id={assignment_id_1}"
        )

    response_data = r.json()
    assert response_data["success"] is True
    assert len(response_data["value"]) == 3
