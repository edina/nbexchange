from dateutil.parser import parse as date_util_parse
from sqlalchemy import text
from tornado import web

from nbexchange.database import scoped_session
from nbexchange.handlers.base import BaseHandler, authenticated
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
            role: {
                $role: str,
                $count: Int
            },
            user_id: {
                $user_id: Str,
                $count: Int
            },
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

        # This gets a bit complicated: we need to separate the role from the courses & actions because
        # when a user has both roles on a course, a single query create a duplicate row for each role.
        # We avoid this by getting the roles separately, then merge them into the final model.
        params = {"user_id": this_user["id"]}

        with scoped_session() as session:
            query = """
            SELECT
              c.id as course_id,
              c.course_code,
              c.course_title,
              ass.id as assignment_id,
              ass.assignment_code,
              act.id as action_id,
              act.user_id,
              u.name,
              act.action,
              act.location,
              act.timestamp
            FROM course c, assignment ass, action act, "user" u
            WHERE act.user_id=u.id
              and act.assignment_id=ass.id
              and ass.course_id=c.id
              and ass.active=True
              and c.id in (
                SELECT s.course_id
                FROM subscription s
                WHERE s.user_id=:user_id
                )
            """

            if course_id_param and course_id_param != "moot":
                query += " AND c.course_code = :course_code"
                params["course_code"] = course_id_param

            if action_param:
                query += " AND act.action=:action"
                params["action"] = action_param

            query += " ORDER BY c.course_code, ass.assignment_code, act.id ASC"
            rows = session.execute(text(query), params).all()

            self.log.debug(f"History: {len(rows)} rows returned for user {this_user['name']}")

            roles_query = text("SELECT s.course_id, s.role FROM subscription s WHERE s.user_id=:this_user_id")
            params["this_user_id"] = this_user["id"]
            roles_rows = session.execute(roles_query, params).all()
            course_roles = {}
            for role_row in roles_rows:
                if role_row.course_id not in course_roles:
                    course_roles[role_row.course_id] = {}
                if role_row.role not in course_roles[role_row.course_id]:
                    course_roles[role_row.course_id][role_row.role] = 1

            models = {}
            for row in rows:
                course_is_instructor = "Instructor" in course_roles.get(row.course_id, {})
                if course_is_instructor:
                    pass
                elif row.action != "released" and row.user_id != this_user["id"]:
                    self.log.debug(
                        f"History: skipping : {row.action} != 'released' and user {row.user_id} != {this_user['id']}"
                    )
                    continue

                # set up the top-level course model if it doesn't exist yet.
                # `user_id` is a dict to note who the querant is... I never promised great code.
                if row.course_id not in models:
                    models[row.course_id] = {
                        "user_id": {this_user["id"]: 1},
                        "role": course_roles.get(row.course_id, {}),
                        "isInstructor": course_is_instructor,
                        "assignments": {},
                        "course_id": row.course_id,
                        "course_code": row.course_code,
                        "course_title": row.course_title,
                    }

                # Now set up the assignment sub-models if they doesn't exist already.
                if row.assignment_id not in models[row.course_id]["assignments"]:
                    models[row.course_id]["assignments"][row.assignment_id] = {
                        "assignment_id": row.assignment_id,
                        "assignment_code": row.assignment_code,
                        "actions": [],
                        "action_summary": {},
                    }

                if row.action not in models[row.course_id]["assignments"][row.assignment_id]["action_summary"]:
                    models[row.course_id]["assignments"][row.assignment_id]["action_summary"][row.action] = 0
                models[row.course_id]["assignments"][row.assignment_id]["action_summary"][row.action] += 1

                this_action = {
                    # because the jlab extensions expects this format... :sigh:
                    "action": "AssignmentActions." + str(row.action),
                    "path": row.location,
                    # timestamp comes through as a string - but lets be sure it has a timezone!
                    "timestamp": self.check_timezone(date_util_parse(str(row.timestamp))).strftime(
                        self.timestamp_format
                    ),
                    "user": row.name,
                }
                models[row.course_id]["assignments"][row.assignment_id]["actions"].append(this_action)

        for course_data in models.values():
            course_data["assignments"] = list(course_data["assignments"].values())

        self.log.debug(f"History returning : {len(models)} items")
        self.finish({"success": True, "value": sorted(models.values(), key=lambda x: (x["course_id"]))})

    def post(self):
        raise web.HTTPError(501)
