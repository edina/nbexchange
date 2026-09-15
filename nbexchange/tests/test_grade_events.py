from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from nbexchange.database import scoped_session
from nbexchange.grade_events import (
    publish_pending_grade_events,
    record_grade_ready_event,
)
from nbexchange.models.actions import Action, AssignmentActions
from nbexchange.models.assignments import Assignment
from nbexchange.models.courses import Course
from nbexchange.models.grade_events import GradeEventOutbox
from nbexchange.models.users import User
from nbexchange.tests.utils import clear_database  # noqa: F401


def create_event():
    with scoped_session() as session:
        course = Course(org_id=42, course_code="BIO101")
        learner = User(org_id=42, name="42-student")
        instructor = User(org_id=42, name="42-instructor")
        session.add_all([course, learner, instructor])
        session.flush()
        assignment = Assignment(course_id=course.id, assignment_code="assignment-1")
        session.add(assignment)
        session.flush()
        action = Action(
            user_id=instructor.id,
            assignment_id=assignment.id,
            action=AssignmentActions.feedback_released,
            timestamp=datetime.now(timezone.utc),
        )
        session.add(action)
        return record_grade_ready_event(
            session,
            action=action,
            course=course,
            assignment=assignment,
            learner=learner,
        ).event_id


@pytest.mark.gen_test
def test_publisher_marks_event_only_after_api_acceptance(clear_database):  # noqa: F811
    event_id = create_event()
    client = SimpleNamespace(fetch=AsyncMock(return_value=SimpleNamespace(code=202)))

    result = yield publish_pending_grade_events(
        "http://noteable-api/grade-events/",
        "service-token",
        http_client=client,
    )

    assert result == {"published": 1, "failed": 0}
    request = client.fetch.call_args.args[0]
    assert request.headers["Authorization"] == "Bearer service-token"
    assert request.headers["Idempotency-Key"] == event_id
    with scoped_session() as session:
        event = session.query(GradeEventOutbox).filter_by(event_id=event_id).one()
        assert event.published_at is not None
        assert event.attempt_count == 1


@pytest.mark.gen_test
def test_failed_publication_stays_in_outbox_for_retry(clear_database):  # noqa: F811
    event_id = create_event()
    client = SimpleNamespace(fetch=AsyncMock(return_value=SimpleNamespace(code=503)))

    result = yield publish_pending_grade_events(
        "http://noteable-api/grade-events/",
        "service-token",
        http_client=client,
    )

    assert result == {"published": 0, "failed": 1}
    with scoped_session() as session:
        event = session.query(GradeEventOutbox).filter_by(event_id=event_id).one()
        assert event.published_at is None
        assert event.next_attempt_at is not None
        assert event.attempt_count == 1
        assert "503" in event.last_error
