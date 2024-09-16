# import os
# import time
# import uuid

from tornado import web

import nbexchange.models.assignments
import nbexchange.models.courses
import nbexchange.models.notebooks
import nbexchange.models.subscriptions
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
                            timestamp: Str,
                            user: Str
                        },
                        {...},
                    ]
                },
            ],
       },
       {...},
    ]


    """

    urls = ["history"]

    # want to add in stuff so "customer-admin" users see all courses for their org.
    @authenticated
    def get(self):

        models = {}

        [action_param, assignment_id_param, course_code_param] = self.get_params(
            ["action", "assignment_id", "course_code"]
        )

        # Python 3.12 required to do "str" in Enum so use __members__ instead
        if action_param and action_param not in AssignmentActions.__members__:
            note = f"{action_param} is not a valid assignment action."
            self.log.info(note)
            self.finish({"success": False, "note": note, "value": []})
            return

        # Who is my user?
        this_user = self.nbex_user
        self.log.debug(f"History authenticated User: {this_user.get('name')}")

        # Find all the assignments this user should be able to see
        with scoped_session() as session:
            subscriptions_query = session.query(nbexchange.models.Subscription).filter_by(user_id=this_user["id"])
            if course_code_param:
                subscriptions_query = subscriptions_query.filter(
                    nbexchange.models.Subscription.course.has(course_code=course_code_param)
                )

            subscriptions = subscriptions_query.all()
            self.log.debug(f"History rows: {subscriptions}")

            for subscription in subscriptions:
                if subscription.course.id not in models:
                    models[subscription.course.id] = {}
                models[subscription.course.id]["role"] = dict()
                models[subscription.course.id]["user_id"] = dict()
                models[subscription.course.id]["assignments"] = list()
                models[subscription.course.id]["isInstructor"] = False

                models[subscription.course.id]["course_id"] = subscription.course.id
                models[subscription.course.id]["course_code"] = subscription.course.course_code
                models[subscription.course.id]["course_title"] = subscription.course.course_title
                models[subscription.course.id]["role"][subscription.role] = 1
                models[subscription.course.id]["user_id"][subscription.user_id] = 1
                if subscription.role == "Instructor":
                    models[subscription.course.id]["isInstructor"] = True
                self.log.debug(
                    (
                        f"       ... course: {models[subscription.course.id]['course_id']} | ",
                        f"{models[subscription.course.id]['course_code']}",
                    )
                )
                for assignment in subscription.course.assignments:
                    self.log.debug(f"           ... assignment: {assignment}")
                    if assignment_id_param and assignment_id_param != assignment.id:
                        self.log.debug(
                            (
                                f"History: ignoring assignment {assignment.id} because request specified ",
                                f"assignment ID {assignment_id_param}",
                            )
                        )
                        continue

                    if assignment.active:
                        a = dict()
                        a["assignment_id"] = assignment.id
                        a["assignment_code"] = assignment.assignment_code
                        a["actions"] = list()
                        a["action_summary"] = dict()
                        for action in assignment.actions:
                            if (
                                action.action == "released"
                                or action.user_id == this_user["id"]  # noqa: W503
                                or subscription.role == "Instructor"  # noqa: W503
                            ):
                                b = dict()
                                action_string = str(action.action).replace("AssignmentActions.", "")
                                if action_param and action_string != action_param:
                                    self.log.debug(
                                        (
                                            f"History: ignoring action {action_string} because it ",
                                            f"isn't of type {action_param}",
                                        )
                                    )
                                    continue
                                if action_string not in a["action_summary"]:
                                    a["action_summary"][action_string] = 0
                                a["action_summary"][action_string] += 1
                                b["action"] = str(action.action)
                                self.log.debug(f"action: {action}")
                                b["timestamp"] = action.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f %Z")
                                user = nbexchange.models.users.User.find_by_pk(db=session, pk=action.user_id)
                                b["user"] = user.name
                                a["actions"].append(b)
                        models[subscription.course.id]["assignments"].append(a)

        self.finish({"success": True, "value": sorted(models.values(), key=lambda x: (x["course_id"]))})

    # This has no authentiction wrapper, so false implication os service
    def post(self):
        raise web.HTTPError(501)
