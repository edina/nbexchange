from tornado import web

import nbexchange.models
import nbexchange.models.subscriptions
from nbexchange.database import scoped_session
from nbexchange.handlers.base import BaseHandler, authenticated
from nbexchange.models.action_history_view import ActionHistoryView
from nbexchange.models.actions import AssignmentActions

"""
All URLs relative to /services/nbexchange

This relys on users being logged in, and the user-object having additional data:
'role' (as per LTI)
"""


class History(BaseHandler):
    """.../actions/
    parmas:
        action: action string - optional. If provided, only returns actions of this type.
        course_id: course code string - optional
        course_code: course code string - optional. Depreciated.

    "action string" must be one of the values in nbexchange.models.actions.AssignmentActions

    GET: gets list of actions relevent to the user.

    It returns all the courses the user is subscribed to, all
    the assignments for those courses, then all appropriate
    actions

    An "appropriate action" depends in the role the user
    has/had for that course: If they were a student, it
    lists the 'release' action and any actions performed by
    the user. If the user was an Instructor, it lists ALL
    actions.

    Returns a list of data:

    [
        {
            course_id: Int,
            course_code: Str,
            course_title: Str,
            role: [Str, Str, ..],
            user_id: [Str, Str, ..],
            isInstructor: Bool,
            assignments: [
                {
                    assignment_code: Str,
                    assignment_id: Int
                    actions: [
                        {
                            action: Str,
                            path: Str,
                            timestamp: Str,
                            user: Str
                        },
                        {...},
                    ],
                    "action_summary": {
                        "released": Int
                        "submitted": Int
                        ...
                    },

                },
            ],
       },
       {...},
    ]

    ..... for the list of possible "action_summary" entries, see values listed in
    nbexchange.models.actions.AssignmentActions

    """

    urls = ["history"]

    @authenticated
    def get(self):

        [action_param, course_id_param, course_code_param] = self.get_params(["action", "course_id", "course_code"])

        if course_code_param:
            self.log.info(
                "History: course_code parameter is deprecated and will be removed in a future release. Please use course_id instead."  # noqa: E501
            )
        if course_code_param and not course_id_param:
            course_id_param = course_code_param

        if action_param and action_param not in AssignmentActions.__members__:
            note = f"{action_param} is not a valid assignment action."
            self.log.info(note)
            self.finish({"success": False, "note": note, "value": []})
            return

        this_user = self.nbex_user
        self.log.debug(f"History authenticated User: {this_user.get('name')}")

        with scoped_session() as session:

            rows = session.query(nbexchange.models.Subscription).all()
            self.log.info(f"subscriptions: {len(rows)}\n {rows}")
            rows = session.query(nbexchange.models.Course).all()
            self.log.info(f"courses: {len(rows)}\n {rows}")
            rows = session.query(nbexchange.models.Assignment).all()
            self.log.info(f"assignments: {len(rows)}\n {rows}")
            rows = session.query(nbexchange.models.Action).all()
            self.log.info(f"actions: {len(rows)}\n {rows}")
            rows = session.query(ActionHistoryView).all()
            self.log.info(f"view: {len(rows)}\n {rows}")

            query = session.query(ActionHistoryView).filter(ActionHistoryView.viewer_user_id == this_user["id"])

            if course_id_param and course_id_param != "moot":
                query = query.filter(ActionHistoryView.course_code == course_id_param)

            if action_param:
                query = query.filter(ActionHistoryView.action == action_param)
            self.log.info(f"History: query: {query}")
            rows = query.all()
            self.log.info(f"History: {len(rows)} rows returned for user {this_user['name']}")
            self.log.info(rows)
            models = {}
            for row in rows:
                if row.viewer_role == "Instructor":
                    pass
                elif row.action != AssignmentActions.released and row.actor_user_id != this_user["id"]:
                    continue

                if row.course_id not in models:
                    models[row.course_id] = {
                        "role": {row.viewer_role: 1},
                        "user_id": {row.viewer_user_id: 1},
                        "assignments": {},
                        "isInstructor": row.viewer_role == "Instructor",
                        "course_id": row.course_id,
                        "course_code": row.course_code,
                        "course_title": row.course_title,
                    }

                models[row.course_id]["role"][row.viewer_role] = 1

                if row.assignment_id not in models[row.course_id]["assignments"]:
                    models[row.course_id]["assignments"][row.assignment_id] = {
                        "assignment_id": row.assignment_id,
                        "assignment_code": row.assignment_code,
                        "actions": [],
                        "action_summary": {},
                    }

                action_string = str(row.action).replace("AssignmentActions.", "")
                if action_string not in models[row.course_id]["assignments"][row.assignment_id]["action_summary"]:
                    models[row.course_id]["assignments"][row.assignment_id]["action_summary"][action_string] = 0
                models[row.course_id]["assignments"][row.assignment_id]["action_summary"][action_string] += 1

                this_action = {
                    "action": str(row.action),
                    "path": row.location,
                    "timestamp": self.check_timezone(row.timestamp).strftime(self.timestamp_format),
                    "user": row.actor_name,
                }
                models[row.course_id]["assignments"][row.assignment_id]["actions"].append(this_action)

            for course_data in models.values():
                course_data["assignments"] = list(course_data["assignments"].values())

        self.finish({"success": True, "value": sorted(models.values(), key=lambda x: (x["course_id"]))})

    def post(self):
        raise web.HTTPError(501)
