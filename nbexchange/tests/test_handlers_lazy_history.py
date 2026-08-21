import shutil
from urllib.parse import urlencode
from unittest.mock import patch

import pytest

from nbexchange.database import scoped_session
from nbexchange.handlers.base import BaseHandler
from nbexchange.models import Action
from nbexchange.models.actions import AssignmentActions
from nbexchange.tests.utils import (  # noqa: F401
    async_requests,
    clear_database,
    get_files_dict,
    user_kiz_instructor,
    user_zik_student,
)

release_files, _, _ = get_files_dict()


@pytest.mark.gen_test
def test_lazy_history_loads_courses_then_assignment_summaries(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        response = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
        assert response.status_code == 200

        response = yield async_requests.get(app.url + "/history/courses")
        assert response.status_code == 200
        courses = response.json()
        assert courses == {
            "success": True,
            "items": [
                {
                    "id": 1,
                    "code": "course_2",
                    "title": "A title",
                    "roles": ["Instructor"],
                    "is_instructor": True,
                    "is_current": True,
                    "assignment_count": 1,
                }
            ],
        }

        response = yield async_requests.get(app.url + "/history/courses/1/assignments")
        assert response.status_code == 200
        assignments = response.json()
        assert assignments["success"] is True
        assert assignments["roles"] == ["Instructor"]
        assert assignments["is_instructor"] is True
        assert len(assignments["items"]) == 1
        assert assignments["items"][0]["id"] == 1
        assert assignments["items"][0]["code"] == "assign_a"
        assert assignments["items"][0]["action_summary"] == {"released": 1}
        assert assignments["items"][0]["first_action_at"] is not None
        assert assignments["items"][0]["last_action_at"] is not None

    shutil.rmtree(app.base_storage_location)


@pytest.mark.gen_test
def test_lazy_history_actions_use_stable_cursor_pagination(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        for _ in range(2):
            response = yield async_requests.post(
                app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
                files=release_files,
            )
            assert response.status_code == 200

        response = yield async_requests.get(app.url + "/history/assignments/1/actions?limit=1&action=released")
        assert response.status_code == 200
        first_page = response.json()
        assert first_page["success"] is True
        assert len(first_page["items"]) == 1
        assert first_page["items"][0]["action"] == "AssignmentActions.released"
        assert first_page["next_cursor"] is not None

        query = urlencode(
            {
                "limit": 1,
                "action": "released",
                "cursor": first_page["next_cursor"],
                "snapshot": first_page["snapshot"],
            }
        )
        response = yield async_requests.get(app.url + f"/history/assignments/1/actions?{query}")
        assert response.status_code == 200
        second_page = response.json()
        assert second_page["success"] is True
        assert len(second_page["items"]) == 1
        assert second_page["items"][0]["id"] != first_page["items"][0]["id"]
        assert second_page["next_cursor"] is None
        assert second_page["snapshot"] == first_page["snapshot"]

    shutil.rmtree(app.base_storage_location)


@pytest.mark.gen_test
def test_lazy_history_rejects_unsubscribed_course(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        response = yield async_requests.get(app.url + "/history/courses/999/assignments")
    assert response.status_code == 404


@pytest.mark.gen_test
def test_lazy_history_student_only_sees_releases_and_own_actions(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        response = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
        assert response.status_code == 200

    # Create the student and their subscription before recording representative actions.
    with patch.object(BaseHandler, "get_current_user", return_value=user_zik_student):
        response = yield async_requests.get(app.url + "/history/courses")
        assert response.status_code == 200

    with scoped_session() as session:
        session.add_all(
            [
                Action(user_id=1, assignment_id=1, action=AssignmentActions.submitted),
                Action(user_id=2, assignment_id=1, action=AssignmentActions.submitted),
            ]
        )

    with patch.object(BaseHandler, "get_current_user", return_value=user_zik_student):
        response = yield async_requests.get(app.url + "/history/courses/1/assignments")
        assert response.status_code == 200
        assignment = response.json()["items"][0]
        assert assignment["action_summary"] == {"released": 1, "submitted": 1}

        response = yield async_requests.get(app.url + "/history/assignments/1/actions?action=submitted")
        assert response.status_code == 200
        actions = response.json()["items"]
        assert len(actions) == 1
        assert actions[0]["user_id"] == 2

    shutil.rmtree(app.base_storage_location)
