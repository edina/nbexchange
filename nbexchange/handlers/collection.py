import datetime
import os
import re
import time
import uuid

from dateutil.tz import gettz
from nbexchange import orm
from nbexchange.base import BaseHandler
from tornado import web, httputil
from urllib.parse import quote_plus
from urllib.request import urlopen

"""
All URLs relative to /services/nbexchange

This relys on users being logged in, and the user-object having additional data:
'role' (as per LTI)
"""


class Collections(BaseHandler):
    """.../collections/
    parmas:
        course_id: course_code
        assignment_id: assignment_code

    GET: gets list of actions for the assignment
    """

    urls = ["collections"]

    @web.authenticated
    def get(self):

        models = []

        [course_code, assignment_code] = self.get_params(["course_id", "assignment_id"])

        if not (course_code and assignment_code):
            note = "Collections call requires both a course code and an assignment code"
            self.log.info(note)
            self.write({"success": False, "note": note})
            return

        # Who is my user?
        this_user = self.nbex_user
        self.log.debug(f"User: {this_user.get('name')}")
        # For what course do we want to see the assignments?
        self.log.debug(f"Course: {course_code}")
        # Is our user subscribed to this course?
        if course_code not in this_user["courses"]:
            note = f"User not subscribed to course {course_code}"
            self.log.info(note)
            self.write({"success": False, "value": models, "note": note})
            return
        if (
            not "instructor" == this_user["current_role"].casefold()
        ):  # we may need to revisit this
            note = f"User not an instructor to course {course_code}"
            self.log.info(note)
            self.write({"success": False, "note": note})
            return

        # Find the course being referred to
        course = orm.Course.find_by_code(
            db=self.db, code=course_code, org_id=this_user["org_id"], log=self.log
        )
        if not course:
            note = f"Course {course_code} does not exist"
            self.log.info(note)
            self.write({"success": False, "value": models, "note": note})
            return

        assignments = orm.Assignment.find_for_course(
            db=self.db, course_id=course.id, log=self.log
        )

        for assignment in assignments:
            self.log.debug(f"Assignment: {assignment}")
            self.log.debug(f"Assignment Actions: {assignment.actions}")
            for action in assignment.actions:
                # For every action that is not "released" checked if the user id matches
                if action.action == orm.AssignmentActions.submitted:
                    models.append(
                        {
                            "assignment_id": assignment.assignment_code,
                            "course_id": assignment.course.course_code,
                            "status": action.action.value,  # currently called 'action' in our db
                            "path": action.location,
                            "notebooks": [
                                {"name": x.name} for x in assignment.notebooks
                            ],
                            "timestamp": action.timestamp.strftime(
                                "%Y-%m-%d %H:%M:%S.%f %Z"
                            ),
                        }
                    )

        self.log.debug(f"Assignments: {models}")
        self.write({"success": True, "value": models})

    # This has no authentiction wrapper, so false implication os service
    def post(self):
        raise web.HTTPError(501)


class Collection(BaseHandler):
    """.../collection/
    parmas:
        course_id: course_code
        assignment_id: assignment_code
        path: url_encoded_path

    GET: Downloads the specified file (checking that it's "submitted", for this course/assignment,
    and the user has access to do so)
    """

    urls = ["collection"]

    @web.authenticated
    def get(self):

        models = []

        [course_code, assignment_code, path] = self.get_params(
            ["course_id", "assignment_id", "path"]
        )

        if not (course_code and assignment_code and path):
            note = (
                "Collection call requires a course code, an assignment code, and a path"
            )
            self.log.info(note)
            self.write({"success": False, "note": note})
            return

        # Who is my user?
        this_user = self.nbex_user
        self.log.debug(f"User: {this_user.get('name')}")
        # For what course do we want to see the assignments?
        self.log.debug(f"Course: {course_code}")
        # Is our user subscribed to this course?
        if course_code not in this_user["courses"]:
            note = f"User not subscribed to course {course_code}"
            self.log.info(note)
            self.write({"success": False, "note": note})
            return
        self.log.info(f"user: {this_user}")

        if (
            not "instructor" == this_user["current_role"].casefold()
        ):  # we may need to revisit this
            note = f"User not an instructor to course {course_code}"
            self.log.info(note)
            self.write({"success": False, "note": note})
            return

        # Find the course being referred to
        course = orm.Course.find_by_code(
            db=self.db, code=course_code, org_id=this_user["org_id"], log=self.log
        )
        if not course:
            note = f"Course {course_code} does not exist"
            self.log.info(note)
            self.write({"success": False, "note": note})
            return

        assignments = orm.Assignment.find_for_course(
            db=self.db, course_id=course.id, log=self.log
        )

        data = b""
        self._headers = httputil.HTTPHeaders(
            {
                "Content-Type": "application/gzip",
                "Date": httputil.format_timestamp(time.time()),
            }
        )

        for assignment in assignments:
            self.log.debug(f"Assignment: {assignment}")
            self.log.debug(f"Assignment Actions: {assignment.actions}")
            for action in assignment.actions:

                # the path should be unique, but lets just double-check its "submitted" too
                if (
                    action.action == orm.AssignmentActions.submitted
                    and action.location == path
                ):

                    try:
                        handle = open(path, "r+b")
                        data = handle.read()
                        handle.close
                    except Exception as e:  # TODO: exception handling
                        self.log.warning(f"Error: {e}")  # TODO: improve error message
                        self.log.info("Recovery failed")

                        # error 500??
                        raise Exception

                    action = orm.Action(
                        user_id=this_user["ormUser"].id,
                        assignment_id=assignment.id,
                        action=orm.AssignmentActions.collected,
                        location=path,
                    )
                    self.db.add(action)
                    self.db.commit()

        self.write(data)

    # This has no authentiction wrapper, so false implication os service
    def post(self):
        raise web.HTTPError(501)
