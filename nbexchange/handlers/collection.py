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

Collection calls:
.../collections?course_id=$course_code?assignment_id=assignment_code
GET: returns list of actions for the assignment


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

        # Endpoint needs to be called with a course_id parameters
        course_code = (
            self.request.arguments["course_id"][0].decode("utf-8")
            if "course_id" in self.request.arguments
            else None
        )
        assignment_code = (
            self.request.arguments["assignment_id"][0].decode("utf-8")
            if "assignment_id" in self.request.arguments
            else None
        )
        if not course_code:
            note = "collections call requires a course id"
            self.log.info(note)
            self.write({"success": False, "value": models, "note": note})
        if not assignment_code:
            note = "collections call requires an assignment id"
            self.log.info(note)
            self.write({"success": False, "value": models, "note": note})

        # Un url-encode variables
        course_code = self.param_decode(course_code)
        assignment_code = self.param_decode(assignment_code)

        # Who is my user?
        this_user = self.nbex_user
        self.log.debug(f"User: {this_user.get('name')}")
        # For what course do we want to see the assignments?
        self.log.debug(f"Course: {course_code}")
        # Is our user subscribed to this course?
        if course_code not in this_user["courses"]:
            note = "User {} not subscribed to course {}".format(
                this_user.get("name"), course_code
            )
            self.log.info(note)
            self.write({"success": False, "value": models, "note": note})
        if not "instructor" in this_user["courses"][course_code]:
            note = "User not an instructor to course {}".format(course_code)
            self.log.info(note)
            self.write({"success": False, "note": note})

        # Find the course being referred to
        course = orm.Course.find_by_code(
            db=self.db, code=course_code, org_id=this_user["org_id"], log=self.log
        )
        if not course:
            note = "Course {} does not exist".format(course_code)
            self.log.info(note)
            self.write({"success": False, "value": models, "note": note})

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

        self.log.debug("Assignments: {}".format(models))
        self.write({"success": True, "value": models})

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

        # Endpoint needs to be called with a course_id parameters
        course_code = (
            self.request.arguments["course_id"][0].decode("utf-8")
            if "course_id" in self.request.arguments
            else None
        )
        assignment_code = (
            self.request.arguments["assignment_id"][0].decode("utf-8")
            if "assignment_id" in self.request.arguments
            else None
        )
        path = (
            self.request.arguments["path"][0].decode("utf-8")
            if "path" in self.request.arguments
            else None
        )
        if not course_code:
            note = "collection call requires a course id"
            self.log.info(note)
            self.write({"success": False, "value": models, "note": note})
        if not assignment_code:
            note = "collection call requires an assignment id"
            self.log.info(note)
            self.write({"success": False, "value": models, "note": note})
        if not path:
            note = "collection call requires a path"
            self.log.info(note)
            self.write({"success": False, "value": models, "note": note})

        # Un url-encode variables
        course_code = self.param_decode(course_code)
        assignment_code = self.param_decode(assignment_code)
        path = self.param_decode(path)

        # Who is my user?
        this_user = self.nbex_user
        self.log.debug(f"User: {this_user.get('name')}")
        # For what course do we want to see the assignments?
        self.log.debug(f"Course: {course_code}")
        # Is our user subscribed to this course?
        if course_code not in this_user["courses"]:
            note = "User {} not subscribed to course {}".format(
                this_user.get("name"), course_code
            )
            self.log.info(note)
            self.write({"success": False, "value": models, "note": note})
        if not "instructor" in this_user["courses"][course_code]:
            note = "User not an instructor to course {}".format(course_code)
            self.log.info(note)
            self.write({"success": False, "note": note})

        # Find the course being referred to
        course = orm.Course.find_by_code(
            db=self.db, code=course_code, org_id=this_user["org_id"], log=self.log
        )
        if not course:
            note = "Course {} does not exist".format(course_code)
            self.log.info(note)
            self.write({"success": False, "value": models, "note": note})


        assignments = orm.Assignment.find_for_course(
            db=self.db, course_id=course.id, log=self.log
        )

        data = b""
        for assignment in assignments:
            self.log.debug(f"Assignment: {assignment}")
            self.log.debug(f"Assignment Actions: {assignment.actions}")
            for action in assignment.actions:
                # the path should be unique, but lets just double-check its "submitted" too
                if (
                    action.action == orm.AssignmentActions.submitted
                    and
                    action.location == path ):

                        try:
                            handle = open(path, "r+b")
                            data = handle.read()
                            handle.close
                        except Exception as e:  # TODO: exception handling
                            self.log.warning(f"Error: {e}")  # TODO: improve error message
                            self.log.info("Recovery failed")

                            # error 500??
                            raise Exception
        self.write(data)
