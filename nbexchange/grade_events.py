import json
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from nbexchange.database import scoped_session
from nbexchange.models.grade_events import GradeEventOutbox


def record_grade_ready_event(session, *, action, course, assignment, learner):
    session.flush()
    source_revision = f"feedback:{action.id}:learner:{learner.id}"
    event = GradeEventOutbox(
        event_id=str(uuid.uuid4()),
        org_id=course.org_id,
        course_id=course.id,
        course_code=course.course_code,
        assignment_id=assignment.id,
        assignment_code=assignment.assignment_code,
        learner_id=learner.id,
        learner_name=learner.name,
        source_revision=source_revision,
        occurred_at=action.timestamp,
    )
    session.add(event)
    return event


def _pending_event_ids(limit):
    now = datetime.now(timezone.utc)
    with scoped_session() as session:
        return [
            row.event_id
            for row in session.query(GradeEventOutbox)
            .filter(
                GradeEventOutbox.published_at.is_(None),
                or_(GradeEventOutbox.next_attempt_at.is_(None), GradeEventOutbox.next_attempt_at <= now),
            )
            .order_by(GradeEventOutbox.occurred_at, GradeEventOutbox.event_id)
            .limit(limit)
        ]


async def publish_pending_grade_events(endpoint, service_token, *, batch_size=100, http_client=None, log=None):
    if not endpoint or not service_token:
        return {"published": 0, "failed": 0}
    client = http_client or AsyncHTTPClient()
    counts = {"published": 0, "failed": 0}
    for event_id in _pending_event_ids(batch_size):
        with scoped_session() as session:
            event = session.query(GradeEventOutbox).filter_by(event_id=event_id).one()
            payload = event.payload()
        request = HTTPRequest(
            endpoint,
            method="POST",
            headers={
                "Authorization": f"Bearer {service_token}",
                "Content-Type": "application/json",
                "Idempotency-Key": event_id,
            },
            body=json.dumps(payload).encode(),
            request_timeout=10,
        )
        try:
            response = await client.fetch(request, raise_error=False)
            if not 200 <= response.code < 300:
                raise RuntimeError(f"Noteable event intake returned HTTP {response.code}")
        except Exception as exc:
            counts["failed"] += 1
            with scoped_session() as session:
                event = session.query(GradeEventOutbox).filter_by(event_id=event_id).one()
                event.attempt_count += 1
                delay = min(3600, 30 * (2 ** min(event.attempt_count - 1, 7)))
                event.next_attempt_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
                event.last_error = str(exc)[:2000]
            if log:
                log.warning("Grade event publication failed: event_id=%s error=%s", event_id, type(exc).__name__)
            continue
        counts["published"] += 1
        with scoped_session() as session:
            event = session.query(GradeEventOutbox).filter_by(event_id=event_id).one()
            event.attempt_count += 1
            event.published_at = datetime.now(timezone.utc)
            event.next_attempt_at = None
            event.last_error = ""
    return counts
