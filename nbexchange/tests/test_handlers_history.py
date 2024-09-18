import logging

import pytest
from mock import patch

from nbexchange.handlers.base import BaseHandler
from nbexchange.tests.test_handlers_base import BaseTestHandlers
from nbexchange.tests.utils import (  # noqa: F401 "action_*" & "clear_database"
    action_collected,
    action_feedback_released,
    action_fetched,
    action_submitted,
    async_requests,
    clear_database,
    user_kiz_instructor,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


class TestHandlersHistory(BaseTestHandlers):

    # require authenticated user (404 because the bounce to login fails)
    @pytest.mark.gen_test
    def test_history_must_be_authenticated(self, app, clear_database):  # noqa: F811
        r = yield async_requests.get(app.url + "/history")
        assert r.status_code == 403

    @pytest.mark.gen_test
    def test_history_invalid_action_param(self, app, clear_database):  # noqa: F811
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            r = yield async_requests.get(app.url + "/history?action=foo")
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["success"] is False
        assert response_data["note"] == "foo is not a valid assignment action."

    @pytest.mark.gen_test
    def test_history_no_action_param(self, app, clear_database, action_submitted):  # noqa: F811
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
                "assignments": [
                    {
                        "assignment_id": 1,
                        "assignment_code": "tree 1",
                        "actions": [
                            {
                                "action": "AssignmentActions.submitted",
                                "timestamp": "1970-01-02 10:10:00.000000 ",
                                "user": "Johaannes",
                            }
                        ],
                        "action_summary": {"submitted": 1},
                    }
                ],
                "isInstructor": True,
                "course_id": 1,
                "course_code": "course_2",
                "course_title": "A title",
            }
        ]

    # Instructor should be able to see feedback_released action by another instructor
    @pytest.mark.gen_test
    def test_history_feedback_released(
        self, app, clear_database, action_submitted, action_feedback_released  # noqa: F811
    ):
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            r = yield async_requests.get(app.url + "/history")
        assert r.status_code == 200
        response_data = r.json()
        print(response_data)
        assert response_data["success"] is True
        assert "value" in response_data
        assert response_data["value"] == [
            {
                "role": {"Instructor": 1},
                "user_id": {"3": 1},
                "assignments": [
                    {
                        "assignment_id": 1,
                        "assignment_code": "tree 1",
                        "actions": [
                            {
                                "action": "AssignmentActions.submitted",
                                "timestamp": "1970-01-02 10:10:00.000000 ",
                                "user": "Johaannes",
                            },
                            {
                                "action": "AssignmentActions.feedback_released",
                                "timestamp": "1970-01-31 10:10:00.000000 ",
                                "user": "kaylee",
                            },
                        ],
                        "action_summary": {"submitted": 1, "feedback_released": 1},
                    }
                ],
                "isInstructor": True,
                "course_id": 1,
                "course_code": "course_2",
                "course_title": "A title",
            }
        ]

    # Filters the response to just actions of feedback_released (so 1 item less that above)
    @pytest.mark.gen_test
    def test_history_action_feedback_released(
        self, app, clear_database, action_submitted, action_feedback_released  # noqa: F811
    ):
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            r = yield async_requests.get(app.url + "/history?action=feedback_released")
        assert r.status_code == 200
        response_data = r.json()
        print(response_data)
        assert response_data["success"] is True
        assert "value" in response_data
        assert response_data["value"] == [
            {
                "role": {"Instructor": 1},
                "user_id": {"3": 1},
                "assignments": [
                    {
                        "assignment_id": 1,
                        "assignment_code": "tree 1",
                        "actions": [
                            {
                                "action": "AssignmentActions.feedback_released",
                                "timestamp": "1970-01-31 10:10:00.000000 ",
                                "user": "kaylee",
                            },
                        ],
                        "action_summary": {"feedback_released": 1},
                    }
                ],
                "isInstructor": True,
                "course_id": 1,
                "course_code": "course_2",
                "course_title": "A title",
            }
        ]

    # returns empty when existing records do not match requested assignment
    @pytest.mark.gen_test
    def test_history_filter_by_assignment_id(
        self, app, clear_database, action_submitted, action_feedback_released  # noqa: F811
    ):
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            r = yield async_requests.get(app.url + "/history?assignment_id=987654321")
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["success"] is True
        assert "value" in response_data
        assert response_data["value"] == [
            {
                "role": {"Instructor": 1},
                "user_id": {"3": 1},
                "assignments": [],
                "isInstructor": True,
                "course_id": 1,
                "course_code": "course_2",
                "course_title": "A title",
            }
        ]

    # returns empty when existing records do not match requested assignment
    @pytest.mark.gen_test
    def test_history_filter_by_course_code_not_exist(
        self, app, clear_database, action_submitted, action_feedback_released  # noqa: F811
    ):
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            r = yield async_requests.get(app.url + "/history?course_code=abcdefghij123456")
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["success"] is True
        assert "value" in response_data
        assert response_data["value"] == []

    @pytest.mark.gen_test
    def test_history_filter_by_course_code_exists(
        self, app, clear_database, action_submitted, action_feedback_released  # noqa: F811
    ):
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            r = yield async_requests.get(app.url + "/history?course_code=course_2")
        assert r.status_code == 200
        response_data = r.json()
        print(response_data)
        assert response_data["success"] is True
        assert "value" in response_data
        assert response_data["value"] == [
            {
                "role": {"Instructor": 1},
                "user_id": {"3": 1},
                "assignments": [
                    {
                        "assignment_id": 1,
                        "assignment_code": "tree 1",
                        "actions": [
                            {
                                "action": "AssignmentActions.submitted",
                                "timestamp": "1970-01-02 10:10:00.000000 ",
                                "user": "Johaannes",
                            },
                            {
                                "action": "AssignmentActions.feedback_released",
                                "timestamp": "1970-01-31 10:10:00.000000 ",
                                "user": "kaylee",
                            },
                        ],
                        "action_summary": {"submitted": 1, "feedback_released": 1},
                    }
                ],
                "isInstructor": True,
                "course_id": 1,
                "course_code": "course_2",
                "course_title": "A title",
            }
        ]
