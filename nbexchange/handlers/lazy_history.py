"""Bounded, lazy-loading history API handlers."""

import base64
import json
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_
from tornado import web

from nbexchange.database import scoped_session
from nbexchange.handlers.base import BaseHandler, authenticated
from nbexchange.models import Action, Assignment, Course, Subscription, User
from nbexchange.models.actions import AssignmentActions

DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000


def _parse_datetime(value, parameter):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as error:
        raise web.HTTPError(400, reason=f"Invalid {parameter}") from error


def _encode_cursor(action):
    payload = json.dumps(
        {"timestamp": action.timestamp.isoformat(), "id": action.id},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_cursor(value):
    try:
        padded = value + "=" * (-len(value) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
        return _parse_datetime(payload["timestamp"], "cursor"), int(payload["id"])
    except web.HTTPError:
        raise
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise web.HTTPError(400, reason="Invalid cursor") from error


class LazyHistoryHandler(BaseHandler):
    """Shared helpers for history resources."""

    def _roles_for_course(self, session, user_id, course_id):
        return [
            role
            for (role,) in session.query(Subscription.role)
            .filter(Subscription.user_id == user_id, Subscription.course_id == course_id)
            .all()
        ]

    def _assignment_access(self, session, user_id, assignment_id):
        assignment = (
            session.query(Assignment).filter(Assignment.id == assignment_id, Assignment.active.is_(True)).first()
        )
        if assignment is None:
            raise web.HTTPError(404)
        roles = self._roles_for_course(session, user_id, assignment.course_id)
        if not roles:
            raise web.HTTPError(404)
        return assignment, roles


class HistoryCourses(LazyHistoryHandler):
    urls = [r"history/courses"]

    @authenticated
    def get(self):
        this_user = self.nbex_user
        roles_by_course = defaultdict(set)

        with scoped_session() as session:
            subscriptions = (
                session.query(Subscription.course_id, Subscription.role)
                .filter(Subscription.user_id == this_user["id"])
                .all()
            )
            for course_id, role in subscriptions:
                roles_by_course[course_id].add(role)

            course_ids = list(roles_by_course)
            if not course_ids:
                self.finish({"success": True, "items": []})
                return

            rows = (
                session.query(Course, func.count(Assignment.id))
                .outerjoin(
                    Assignment,
                    and_(Assignment.course_id == Course.id, Assignment.active.is_(True)),
                )
                .filter(Course.id.in_(course_ids))
                .group_by(Course.id)
                .order_by(Course.course_title, Course.course_code)
                .all()
            )

            items = []
            for course, assignment_count in rows:
                roles = sorted(roles_by_course[course.id])
                items.append(
                    {
                        "id": course.id,
                        "code": course.course_code,
                        "title": course.course_title,
                        "roles": roles,
                        "is_instructor": "Instructor" in roles,
                        "is_current": course.course_code == this_user["current_course"],
                        "assignment_count": assignment_count,
                    }
                )

        self.finish({"success": True, "items": items})


class HistoryCourseAssignments(LazyHistoryHandler):
    urls = [r"history/courses/([0-9]+)/assignments"]

    @authenticated
    def get(self, course_id):
        this_user = self.nbex_user
        course_id = int(course_id)

        with scoped_session() as session:
            roles = self._roles_for_course(session, this_user["id"], course_id)
            if not roles:
                raise web.HTTPError(404)

            assignments = (
                session.query(Assignment)
                .filter(Assignment.course_id == course_id, Assignment.active.is_(True))
                .order_by(Assignment.assignment_code, Assignment.id)
                .all()
            )
            assignment_ids = [assignment.id for assignment in assignments]
            summaries = defaultdict(dict)
            first_actions = {}
            last_actions = {}

            if assignment_ids:
                summary_query = session.query(
                    Action.assignment_id,
                    Action.action,
                    func.count(Action.id),
                    func.min(Action.timestamp),
                    func.max(Action.timestamp),
                ).filter(Action.assignment_id.in_(assignment_ids))
                if "Instructor" not in roles:
                    summary_query = summary_query.filter(
                        or_(
                            Action.action == AssignmentActions.released,
                            Action.user_id == this_user["id"],
                        )
                    )
                rows = summary_query.group_by(Action.assignment_id, Action.action).all()
                for assignment_id, action, count, first_action, last_action in rows:
                    summaries[assignment_id][action.value] = count
                    if assignment_id not in first_actions or first_action < first_actions[assignment_id]:
                        first_actions[assignment_id] = first_action
                    if assignment_id not in last_actions or last_action > last_actions[assignment_id]:
                        last_actions[assignment_id] = last_action

            items = [
                {
                    "id": assignment.id,
                    "code": assignment.assignment_code,
                    "action_summary": summaries[assignment.id],
                    "first_action_at": (
                        first_actions[assignment.id].isoformat() if assignment.id in first_actions else None
                    ),
                    "last_action_at": (
                        last_actions[assignment.id].isoformat() if assignment.id in last_actions else None
                    ),
                }
                for assignment in assignments
            ]

        self.finish(
            {
                "success": True,
                "items": items,
                "roles": sorted(set(roles)),
                "is_instructor": "Instructor" in roles,
            }
        )


class HistoryAssignmentActions(LazyHistoryHandler):
    urls = [r"history/assignments/([0-9]+)/actions"]

    @authenticated
    def get(self, assignment_id):
        this_user = self.nbex_user
        assignment_id = int(assignment_id)

        try:
            limit = int(self.get_argument("limit", str(DEFAULT_PAGE_SIZE)))
        except ValueError as error:
            raise web.HTTPError(400, reason="Invalid limit") from error
        if limit < 1 or limit > MAX_PAGE_SIZE:
            raise web.HTTPError(400, reason=f"limit must be between 1 and {MAX_PAGE_SIZE}")

        action_param = self.get_argument("action", None)
        if action_param and action_param not in AssignmentActions.__members__:
            raise web.HTTPError(400, reason=f"Invalid action: {action_param}")

        snapshot_value = self.get_argument("snapshot", None)
        snapshot = _parse_datetime(snapshot_value, "snapshot") if snapshot_value else datetime.now(timezone.utc)
        cursor_value = self.get_argument("cursor", None)
        cursor = _decode_cursor(cursor_value) if cursor_value else None

        with scoped_session() as session:
            assignment, roles = self._assignment_access(session, this_user["id"], assignment_id)
            is_instructor = "Instructor" in roles

            query = (
                session.query(Action, User.name)
                .join(User, User.id == Action.user_id)
                .filter(Action.assignment_id == assignment.id, Action.timestamp <= snapshot)
            )
            if not is_instructor:
                query = query.filter(
                    or_(
                        Action.action == AssignmentActions.released,
                        Action.user_id == this_user["id"],
                    )
                )
            if action_param:
                query = query.filter(Action.action == AssignmentActions[action_param])
            if cursor:
                cursor_timestamp, cursor_id = cursor
                query = query.filter(
                    or_(
                        Action.timestamp < cursor_timestamp,
                        and_(Action.timestamp == cursor_timestamp, Action.id < cursor_id),
                    )
                )

            rows = query.order_by(Action.timestamp.desc(), Action.id.desc()).limit(limit + 1).all()
            has_more = len(rows) > limit
            rows = rows[:limit]

            items = [
                {
                    "id": action.id,
                    "action": f"AssignmentActions.{action.action.value}",
                    "timestamp": self.check_timezone(action.timestamp).isoformat(),
                    "path": action.location,
                    "user_id": action.user_id,
                    "user": actor_name,
                }
                for action, actor_name in rows
            ]
            next_cursor = _encode_cursor(rows[-1][0]) if has_more and rows else None

        self.finish(
            {
                "success": True,
                "items": items,
                "next_cursor": next_cursor,
                "snapshot": snapshot.isoformat(),
            }
        )
