import re
import time

from tornado import web, httputil

import nbexchange.models.actions
import nbexchange.models.assignments
import nbexchange.models.courses
from nbexchange.database import scoped_session
from nbexchange.handlers.base import BaseHandler, authenticated

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
        user_id: user_id - optional

    GET: gets list of actions for the assignment
    """

    urls = ["collections"]

    @authenticated
    def get(self):

        models = []

        [course_code, assignment_code, user_id] = self.get_params(
            ["course_id", "assignment_id", "user_id"]
        )

        if not (course_code and assignment_code):
            note = "Collections call requires both a course code and an assignment code"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        # set up some regex segments for use later on
        # fr is combining f-string substitution with re's raw-string
        re_action = r"submitted"
        re_course = fr"{course_code}"
        re_assignment = fr"{assignment_code}"
        re_user = fr"{user_id}" if user_id else r"[^/]+"

        # Who is my user?
        this_user = self.nbex_user
        self.log.debug(f"User: {this_user.get('name')}")
        # For what course do we want to see the assignments?
        self.log.debug(f"Course: {course_code}")
        # Is our user subscribed to this course?
        if course_code not in this_user["courses"]:
            note = f"User not subscribed to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return
        if (
            not "instructor" == this_user["current_role"].casefold()
        ):  # we may need to revisit this
            note = f"User not an instructor to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        # Find the course being referred to
        with scoped_session() as session:
            course = nbexchange.models.courses.Course.find_by_code(
                db=session, code=course_code, org_id=this_user["org_id"], log=self.log
            )
            if not course:
                note = f"Course {course_code} does not exist"
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return

            assignments = nbexchange.models.assignments.Assignment.find_for_course(
                db=session, course_id=course.id, log=self.log
            )

            for assignment in assignments:
                self.log.debug(f"Assignment: {assignment}")

                # if an assignment code is given, filter off everything else
                if assignment.assignment_code != assignment_code:
                    continue
                self.log.debug(f"Assignment Actions: {assignment.actions}")
                for action in assignment.actions:
                    if re.search(
                        fr"/{re_action}/{re_course}/{re_assignment}/{re_user}/",
                        action.location,
                    ):
                        models.append(
                            {
                                "assignment_id": assignment.assignment_code,
                                "course_id": assignment.course.course_code,
                                "status": action.action.value,  # currently called 'action' in our db
                                "path": action.location,
                                # 'name' in db, 'notebook_id' id nbgrader
                                "notebooks": [
                                    {"notebook_id": x.name}
                                    for x in assignment.notebooks
                                ],
                                "timestamp": action.timestamp.strftime(
                                    "%Y-%m-%d %H:%M:%S.%f %Z"
                                ),
                            }
                        )

            self.log.debug(f"Assignments: {models}")
        self.finish({"success": True, "value": models})

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

    @authenticated
    def get(self):

        [course_code, assignment_code, path] = self.get_params(
            ["course_id", "assignment_id", "path"]
        )

        if not (course_code and assignment_code and path):
            note = (
                "Collection call requires a course code, an assignment code, and a path"
            )
            self.log.info(note)
            self.finish({"success": False, "note": note})
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
            self.finish({"success": False, "note": note})
            return
        self.log.info(f"user: {this_user}")

        if (
            not "instructor" == this_user["current_role"].casefold()
        ):  # we may need to revisit this
            note = f"User not an instructor to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        # Find the course being referred to
        with scoped_session() as session:
            course = nbexchange.models.courses.Course.find_by_code(
                db=session, code=course_code, org_id=this_user["org_id"], log=self.log
            )
            if not course:
                note = f"Course {course_code} does not exist"
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return

            # We need to key off the assignment, but we're actually looking
            # for the action with a action and a specific path
            assignments = nbexchange.models.assignments.Assignment.find_for_course(
                db=session,
                course_id=course.id,
                log=self.log,
                action=nbexchange.models.actions.AssignmentActions.submitted.value,
                path=path,
            )

            data = b""
            self._headers = httputil.HTTPHeaders(
                {
                    "Content-Type": "application/gzip",
                    "Date": httputil.format_timestamp(time.time()),
                }
            )

            # I do not want to assume there will just be one.
            for assignment in assignments:
                self.log.debug(f"Assignment: {assignment}")
                self.log.debug(f"Assignment Actions: {assignment.actions}")

                release_file = None

                # We will get 0-n submit actions for this path (where n should be 1),
                # we just want the last one
                # Using a reversed for loop as there may be 0 elements :)
                for action in assignment.actions:
                    release_file = action.location
                    break

                if release_file:
                    try:
                        with open(path, "r+b") as handle:
                            data = handle.read()
                    except Exception as e:  # TODO: exception handling
                        self.log.warning(f"Error: {e}")  # TODO: improve error message
                        self.log.info("Recovery failed")

                        # error 500??
                        raise Exception

                    self.log.info(
                        f"Adding action {nbexchange.models.actions.AssignmentActions.collected.value} for user {this_user['id']} against assignment {assignment.id}"
                    )
                    action = nbexchange.models.actions.Action(
                        user_id=this_user["id"],
                        assignment_id=assignment.id,
                        action=nbexchange.models.actions.AssignmentActions.collected,
                        location=path,
                    )
                    session.add(action)

                    self.finish(data)

    # This has no authentiction wrapper, so false implication os service
    def post(self):
        raise web.HTTPError(501)
