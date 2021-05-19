import os
import time
import uuid

from tornado import web

from nbexchange.database import scoped_session
from nbexchange.handlers.base import BaseHandler, authenticated
from nbexchange.models.actions import Action, AssignmentActions
from nbexchange.models.assignments import Assignment
from nbexchange.models.courses import Course

"""
All URLs relative to /services/nbexchange

This relys on users being logged in, and the user-object having additional data:
'role' (as per LTI)
"""


class Submission(BaseHandler):
    """.../submisssion/
    parmas:
        course_id: course_code
        assignment_id: assignment_code

    POST: (with file) submits an assignment"""

    urls = ["submission"]

    # This has no authentiction wrapper, so false implication os service
    def get(self):
        raise web.HTTPError(501)

    # This is a student submitting an assignment, not an instructor "release"
    @authenticated
    def post(self):

        [course_code, assignment_code] = self.get_params(["course_id", "assignment_id"])
        self.log.debug(
            f"Called POST /submission with arguments: course {course_code} and  assignment {assignment_code}"
        )
        if not (course_code and assignment_code):
            note = f"Submission call requires both a course code and an assignment code"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        this_user = self.nbex_user
        if not course_code in this_user["courses"]:
            note = f"User not subscribed to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        # The course will exist: the user object creates it if it doesn't exist
        #  - and we know the user is subscribed to the course as an instructor (above)
        with scoped_session() as session:
            course = Course.find_by_code(
                db=session, code=course_code, org_id=this_user["org_id"], log=self.log
            )

            # We need to find this assignment, or make a new one.
            assignment = Assignment.find_by_code(
                db=session, code=assignment_code, course_id=course.id
            )
            if assignment is None:
                note = f"User not fetched assignment {assignment_code}"
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return

            # storage is dynamically in $path/submitted/$course_code/$assignment_code/$username/<timestamp>/
            # Note - this means that a user can submit multiple times, and we have all copies
            release_file = "/".join(
                [
                    self.base_storage_location,
                    str(this_user["org_id"]),
                    AssignmentActions.submitted.value,
                    course_code,
                    assignment_code,
                    this_user["name"],
                    str(int(time.time())),
                ]
            )

            if not self.request.files:
                self.log.warning(
                    f"Error: No file supplies in upload"
                )  # TODO: improve error message
                raise web.HTTPError(412)  # precondition failed

            try:
                # Write the uploaded file to the desired location
                file_info = self.request.files["assignment"][0]

                filename, content_type = (
                    file_info["filename"],
                    file_info["content_type"],
                )
                note = f"Received file {filename}, of type {content_type}"
                self.log.info(note)
                extn = os.path.splitext(filename)[1]
                cname = str(uuid.uuid4()) + extn

                # store to disk.
                # This should be abstracted, so it can be overloaded to store in other manners (eg AWS)
                release_file = release_file + "/" + cname
                # Ensure the directory exists
                os.makedirs(os.path.dirname(release_file), exist_ok=True)
                with open(release_file, "w+b") as handle:
                    handle.write(file_info["body"])

            except Exception as e:  # TODO: exception handling
                self.log.warning(f"Error: {e}")  # TODO: improve error message

                self.log.info(f"Upload failed")
                # error 500??
                raise web.HTTPError(418)

            # Check the file exists on disk
            if not (os.path.exists(release_file) and os.access(release_file, os.R_OK) and os.path.getsize(release_file) > 0):
                note = "File upload failed."
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return

            # now commit the assignment, and get it back to find the id
            assignment = Assignment.find_by_code(
                db=session, code=assignment_code, course_id=course.id
            )

            # Record the action.
            # Note we record the path to the files.
            self.log.info(
                f"Adding action {AssignmentActions.submitted.value} for user {this_user['id']} against assignment {assignment.id}"
            )
            action = Action(
                user_id=this_user["id"],
                assignment_id=assignment.id,
                action=AssignmentActions.submitted,
                location=release_file,
            )
            session.add(action)
        self.finish({"success": True, "note": "Submitted"})


class Submissions(BaseHandler):
    urls = ["submissions"]

    # This has no authentiction wrapper, so false implication os service
    def get(self):
        raise web.HTTPError(501)

    # This has no authentiction wrapper, so false implication os service
    def post(self):
        raise web.HTTPError(501)
