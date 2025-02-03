import base64
import logging
import sys
from datetime import datetime
from unittest.mock import ANY

import pytest
from mock import patch
from nbgrader.utils import make_unique_key, notebook_hash

from nbexchange.handlers.base import BaseHandler

# from nbexchange.tests.test_handlers_base import BaseTestHandlers
from nbexchange.tests.utils import (  # noqa: F401 "action_*" & "clear_database"
    async_requests,
    clear_database,
    get_feedback_dict,
    get_files_dict,
    timestamp_format,
    tz,
    user_brobbere_student,
    user_kiz,
    user_kiz_instructor,
    user_kiz_student,
    user_lkihlman_instructor,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

# set up the file to be uploaded as part of the testing later
feedback_filename = sys.argv[0]  # ourself :)
feedbacks = get_feedback_dict(feedback_filename)
feedback_base64 = base64.b64encode(open(sys.argv[0]).read().encode("utf-8"))
release_files, notebooks, timestamp = get_files_dict()


# #### POST /history #### #
# No method available (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_collections_no_post_action(app):
    r = yield async_requests.post(app.url + "/collections")
    assert r.status_code == 501


# subscribed user makes no difference (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_collections_no_post_action_even_authenticated(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/collections?course_id=course_2")
    assert r.status_code == 501


# #### GET /history (list available assignments for collection) #### #

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
# #################################
# class TestHandlersHistory(BaseTestHandlers):


# require authenticated user (404 because the bounce to login fails)
@pytest.mark.gen_test
def test_history_must_be_authenticated(app, clear_database):  # noqa: F811
    r = yield async_requests.get(app.url + "/history")
    assert r.status_code == 403


# test that history does not allow unknown "action" values
@pytest.mark.gen_test
def test_history_invalid_action_param(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/history?action=foo")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "foo is not a valid assignment action."


# broken nbex_user throws a 500 error on the server
# (needs to be submitted before it can be seen )
@pytest.mark.gen_test
def test_collections_broken_nbex_user(app, clear_database, caplog):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz):
        r = yield async_requests.get(app.url + "/history")
    assert r.status_code == 500
    assert "Both current_course ('None') and current_role ('None') must have values. User was '1-kiz'" in caplog.text


# history returns valid data
# (needs to be submitted before it can be seen )
@pytest.mark.gen_test
def test_history_no_action_param(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/history")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert "value" in response_data
    assert response_data["value"] == [
        {
            "role": {"Instructor": 1},
            "user_id": {"1": 1},
            "assignments": [
                {
                    "assignment_id": 1,
                    "assignment_code": "assign_a",
                    "actions": [
                        {
                            "action": "AssignmentActions.released",
                            "timestamp": ANY,  # The wonderful <ANY> effectively wildcards this
                            "user": "1-kiz",
                        }
                    ],
                    "action_summary": {"released": 1},
                }
            ],
            "isInstructor": True,
            "course_id": 1,
            "course_code": "course_2",
            "course_title": "A title",
        }
    ]


# history only returns data for courses subscribed to
# (sumbit for course_1, user on course_2)
@pytest.mark.gen_test
def test_history_no_courses_not_suscribed_to(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_lkihlman_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_1&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/history")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert "value" in response_data
    assert response_data["value"] == [
        {
            "role": {"Instructor": 1},
            "user_id": {"2": 1},
            "assignments": [],
            "isInstructor": True,
            "course_id": 2,
            "course_code": "course_2",
            "course_title": "A title",
        }
    ]


# assert we get actions from multiple courses if subscribed to multiple courses
@pytest.mark.gen_test
def test_history_multiple_courses_if_subscribed(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    user_kiz2_instructor = dict(user_kiz_instructor)  # duplicate, not reference
    user_kiz2_instructor["course_id"] = "course_2b"
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz2_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2b&assignment_id=assign_a2",
            files=release_files,
        )

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/history")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert "value" in response_data
    assert response_data["value"] == [
        {
            "role": {"Instructor": 1},
            "user_id": {"1": 1},
            "assignments": [
                {
                    "assignment_id": 1,
                    "assignment_code": "assign_a",
                    "actions": [
                        {
                            "action": "AssignmentActions.released",
                            "timestamp": ANY,
                            "user": "1-kiz",
                        }
                    ],
                    "action_summary": {"released": 1},
                }
            ],
            "isInstructor": True,
            "course_id": 1,
            "course_code": "course_2",
            "course_title": "A title",
        },
        {
            "role": {"Instructor": 1},
            "user_id": {"1": 1},
            "assignments": [
                {
                    "assignment_id": 2,
                    "assignment_code": "assign_a2",
                    "actions": [
                        {
                            "action": "AssignmentActions.released",
                            "timestamp": ANY,
                            "user": "1-kiz",
                        }
                    ],
                    "action_summary": {"released": 1},
                }
            ],
            "isInstructor": True,
            "course_id": 2,
            "course_code": "course_2b",
            "course_title": "A title",
        },
    ]


# assert we get actions from one courses if subscribed to multiple courses, but 1 course named
# (same data as above, but the return should be only 1 course)
@pytest.mark.gen_test
def test_history_actions_filtered_by_course(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    user_kiz2_instructor = dict(user_kiz_instructor)  # duplicate, not reference
    user_kiz2_instructor["course_id"] = "course_2b"
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz2_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2b&assignment_id=assign_a2",
            files=release_files,
        )

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/history?course_code=course_2b")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert "value" in response_data
    assert response_data["value"] == [
        {
            "role": {"Instructor": 1},
            "user_id": {"1": 1},
            "assignments": [
                {
                    "assignment_id": 2,
                    "assignment_code": "assign_a2",
                    "actions": [
                        {
                            "action": "AssignmentActions.released",
                            "timestamp": ANY,
                            "user": "1-kiz",
                        }
                    ],
                    "action_summary": {"released": 1},
                }
            ],
            "isInstructor": True,
            "course_id": 2,
            "course_code": "course_2b",
            "course_title": "A title",
        },
    ]


# assert we get the full suite of actions - just do the 1 course, but have duplicates
# (release twice, instructor & two students submit, 2nd instructor collects,
#  2nd instructor releases feedback for both students, 1st instructor lists history
#  - should see the lot)
@pytest.mark.gen_test
def test_history_full_set_of_actions_with_duplicates(app, clear_database):  # noqa: F811
    notebook = "notebook"

    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
            **kwargs,
        )  # release
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )  # re-release
    # Submissions check for a released action, not a fetched one
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )  # Submitted
    with patch.object(BaseHandler, "get_current_user", return_value=user_brobbere_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )  # Submitted 2nd user
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/collections?course_id=course_2&assignment_id=assign_a")  # collected

    # feedback 1
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key("course_2", "assign_a", "notebook", user_kiz_student["name"], timestamp),
    )
    url = (
        f"/feedback?assignment_id=assign_a"
        f"&course_id=course_2"
        f"&notebook={notebook}"
        f"&student={user_kiz_student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    # feedback 2
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key("course_2", "assign_a", "notebook", user_brobbere_student["name"], timestamp),
    )
    url = (
        f"/feedback?assignment_id=assign_a"
        f"&course_id=course_2"
        f"&notebook={notebook}"
        f"&student={user_brobbere_student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/history")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert "value" in response_data

    assert response_data["value"] == [
        {
            "role": {"Instructor": 1, "Student": 1},
            "user_id": {"1": 1},
            "assignments": ANY,
            "isInstructor": True,
            "course_id": 1,
            "course_code": "course_2",
            "course_title": "A title",
        },
    ]
    the_assignment_data_im_interested_in = response_data["value"][0]["assignments"][0]
    assert len(the_assignment_data_im_interested_in["actions"]) == 6
    assert the_assignment_data_im_interested_in["action_summary"] == {
        "feedback_released": 2,
        "released": 2,
        "submitted": 2,
    }


# Filters the response to just actions of feedback_released
#  (repeat test_history_full_set_of_actions_with_duplicates, but the history query restricts to 'feedback')
@pytest.mark.gen_test
def test_history_action_feedback_released(app, clear_database):  # noqa: F811
    notebook = "notebook"

    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
            **kwargs,
        )  # release
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )  # re-release
    # Submissions check for a released action, not a fetched one
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )  # Submitted
    with patch.object(BaseHandler, "get_current_user", return_value=user_brobbere_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )  # Submitted 2nd user
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/collections?course_id=course_2&assignment_id=assign_a")  # collected

    # feedback 1
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key("course_2", "assign_a", "notebook", user_kiz_student["name"], timestamp),
    )
    url = (
        f"/feedback?assignment_id=assign_a"
        f"&course_id=course_2"
        f"&notebook={notebook}"
        f"&student={user_kiz_student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    # feedback 2
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key("course_2", "assign_a", "notebook", user_brobbere_student["name"], timestamp),
    )
    url = (
        f"/feedback?assignment_id=assign_a"
        f"&course_id=course_2"
        f"&notebook={notebook}"
        f"&student={user_brobbere_student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/history?action=feedback_released")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert "value" in response_data
    assert response_data["value"] == [
        {
            "role": {"Instructor": 1, "Student": 1},
            "user_id": {"1": 1},
            "assignments": [
                {
                    "action_summary": {
                        "feedback_released": 2,
                    },
                    "actions": [
                        {
                            "action": "AssignmentActions.feedback_released",
                            "timestamp": ANY,
                            "user": "1-kiz",
                        },
                        {
                            "action": "AssignmentActions.feedback_released",
                            "timestamp": ANY,
                            "user": "1-kiz",
                        },
                    ],
                    "assignment_code": "assign_a",
                    "assignment_id": 1,
                },
            ],
            "isInstructor": True,
            "course_id": 1,
            "course_code": "course_2",
            "course_title": "A title",
        },
    ]


# Filters the response to just actions of feedback_released
#  (repeast test_history_full_set_of_actions_with_duplicates, but the user has not had isntructor role)
@pytest.mark.gen_test
def test_history_action_students_much_limited(app, clear_database):  # noqa: F811
    notebook = "notebook"

    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
            **kwargs,
        )  # release
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )  # re-release
    # Submissions check for a released action, not a fetched one
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )  # Submitted
    with patch.object(BaseHandler, "get_current_user", return_value=user_brobbere_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )  # Submitted 2nd user
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/collections?course_id=course_2&assignment_id=assign_a")  # collected

    # feedback 1
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key("course_2", "assign_a", "notebook", user_kiz_student["name"], timestamp),
    )
    url = (
        f"/feedback?assignment_id=assign_a"
        f"&course_id=course_2"
        f"&notebook={notebook}"
        f"&student={user_kiz_student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    # feedback 2
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key("course_2", "assign_a", "notebook", user_brobbere_student["name"], timestamp),
    )
    url = (
        f"/feedback?assignment_id=assign_a"
        f"&course_id=course_2"
        f"&notebook={notebook}"
        f"&student={user_brobbere_student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    with patch.object(BaseHandler, "get_current_user", return_value=user_brobbere_student):
        r = yield async_requests.get(app.url + "/history")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert "value" in response_data
    assert response_data["value"] == [
        {
            "role": {"Student": 1},
            "user_id": {"2": 1},
            "assignments": [
                {
                    "action_summary": {
                        "released": 2,
                        "submitted": 1,
                    },
                    "actions": [
                        {
                            "action": "AssignmentActions.released",
                            "timestamp": ANY,
                            "user": "1-kiz",
                        },
                        {
                            "action": "AssignmentActions.released",
                            "timestamp": ANY,
                            "user": "1-kiz",
                        },
                        {
                            "action": "AssignmentActions.submitted",
                            "timestamp": ANY,
                            "user": "1-brobbere",
                        },
                    ],
                    "assignment_code": "assign_a",
                    "assignment_id": 1,
                },
            ],
            "isInstructor": False,
            "course_id": 1,
            "course_code": "course_2",
            "course_title": "A title",
        },
    ]


# # returns empty when existing records do not match requested assignment
# @pytest.mark.gen_test
# def test_history_filter_by_assignment_id(
#     app, clear_database, action_submitted, action_feedback_released  # noqa: F811
# ):
#     with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
#         r = yield async_requests.get(app.url + "/history?assignment_id=987654321")
#     assert r.status_code == 200
#     response_data = r.json()
#     assert response_data["success"] is True
#     assert "value" in response_data
#     assert response_data["value"] == [
#         {
#             "role": {"Instructor": 1},
#             "user_id": {"3": 1},
#             "assignments": [],
#             "isInstructor": True,
#             "course_id": 1,
#             "course_code": "course_2",
#             "course_title": "A title",
#         }
#     ]
