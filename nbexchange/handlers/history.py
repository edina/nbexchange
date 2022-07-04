# import os
# import time
# import uuid

from sqlalchemy import desc
from tornado import httputil, web

import nbexchange.models.assignments
import nbexchange.models.courses
import nbexchange.models.notebooks
import nbexchange.models.subscriptions
from nbexchange.database import scoped_session
from nbexchange.handlers.base import BaseHandler, authenticated

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

        # Who is my user?
        this_user = self.nbex_user
        self.log.debug(f"History authenticated User: {this_user.get('name')}")

        # Find all the assignments this user should be able to see
        with scoped_session() as session:
            rows = session.query(nbexchange.models.Subscription).filter_by(user_id=this_user["id"]).all()

            for row in rows:
                if not row.course.id in models:
                    models[row.course.id] = {}
                data = dict()
                models[row.course.id]["role"] = dict()
                models[row.course.id]["user_id"] = dict()
                models[row.course.id]["assignments"] = list()
                models[row.course.id]["isInstructor"] = False

                models[row.course.id]["course_id"] = row.course.id
                models[row.course.id]["course_code"] = row.course.course_code
                models[row.course.id]["course_title"] = row.course.course_title
                models[row.course.id]["role"][row.role] = 1
                models[row.course.id]["user_id"][row.user_id] = 1
                if row.role == "Instructor":
                    models[row.course.id]["isInstructor"] = True
                self.log.debug(
                    f"       ... course: {models[row.course.id]['course_id']} | {models[row.course.id]['course_code']}"
                )
                for assignment in row.course.assignments:
                    self.log.debug(f"           ... assignment: {assignment}")

                    if assignment.active:
                        a = dict()
                        a["assignment_id"] = assignment.id
                        a["assignment_code"] = assignment.assignment_code
                        a["actions"] = list()
                        a["action_summary"] = dict()
                        for action in assignment.actions:
                            if (
                                action.action == "released"
                                or action.user_id == this_user["id"]
                                or row.role == "Instructor"
                            ):
                                b = dict()
                                action_string = str(action.action).replace("AssignmentActions.", "")
                                if not action_string in a["action_summary"]:
                                    a["action_summary"][action_string] = 0
                                a["action_summary"][action_string] += 1
                                b["action"] = str(action.action)
                                b["timestamp"] = action.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f %Z")
                                user = nbexchange.models.users.User.find_by_pk(db=session, pk=action.user_id)
                                b["user"] = user.name
                                a["actions"].append(b)
                        models[row.course.id]["assignments"].append(a)

        self.finish({"success": True, "value": sorted(models.values(), key=lambda x: (x["course_id"]))})

    # This has no authentiction wrapper, so false implication os service
    def post(self):
        raise web.HTTPError(501)
