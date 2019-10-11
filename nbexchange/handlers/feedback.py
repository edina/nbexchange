import os
import time
import uuid

from sqlalchemy import desc
from tornado import web, httputil

import nbexchange.models.actions
import nbexchange.models.assignments
import nbexchange.models.courses
import nbexchange.models.notebooks
from nbexchange.database import scoped_session
from nbexchange.handlers.base import BaseHandler, authenticated

"""
All URLs relative to /services/nbexchange

This relys on users being logged in, and the user-object having additional data:
'role' (as per LTI)
"""

class Feedback(BaseHandler):
    """.../feedback/
    parmas:
        course_id: course_code
        assignment_id: assignment_code
        user_id: user_id (optional)

    GET: Get list of feedback files for an assignment and user
    POST: (role=instructor, with file): Add ("feedback") to an assignment
    """

    urls = ["feedback"]

    @authenticated
    def get(self):  # def get(self, course_code, assignment_code=None):

        course_code, assignment_code, user_id = self.get_params(["course_id", "assignment_id", "user_id"])

        if not (course_code and assignment_code):
            note = "Assigment call requires both a course code and an assignment code!!"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        this_user = self.nbex_user

        if not course_code in this_user["courses"]:
            note = f"User not subscribed to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        # Find the course being referred to
        with scoped_session() as session:
            

    # This is releasing an **assignment**, not a student submission
    @authenticated
    def post(self):

        [course_code, assignment_code] = self.get_params(["course_id", "assignment_id"])
        self.log.debug(
            f"Called POST /assignment with arguments: course {course_code} and  assignment {assignment_code}"
        )
        if not (course_code and assignment_code):
            note = f"Posting an Assigment requires a course code and an assignment code"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        this_user = self.nbex_user
        if not course_code in this_user["courses"]:
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

        # The course will exist: the user object creates it if it doesn't exist
        #  - and we know the user is subscribed to the course as an instructor (above)
        with scoped_session() as session:
            course = nbexchange.models.courses.Course.find_by_code(
                db=session, code=course_code, org_id=this_user["org_id"], log=self.log
            )

            # We need to find this assignment, or make a new one.
            assignment = nbexchange.models.assignments.Assignment.find_by_code(
                db=session, code=assignment_code, course_id=course.id
            )

            if assignment is None:
                # Look for inactive assignments
                assignment = nbexchange.models.assignments.Assignment.find_by_code(
                    db=session, code=assignment_code, course_id=course.id, active=False
                )

            self.log.warn(f"The value of assignment here is : {assignment}")

            if assignment is None:
                self.log.info(
                    f"New Assignment details: assignment_code:{assignment_code}, course_id:{course.id}"
                )
                # defaults active
                assignment = nbexchange.models.assignments.Assignment(
                    assignment_code=assignment_code, course_id=course.id
                )
                session.add(assignment)
                # deliberately no commit: we need to be able to roll-back if there's no data!

            # Set assignment to active
            assignment.active = True

            # storage is dynamically in $path/release/$course_code/$assignment_code/<timestamp>/
            # Note - this means we can have multiple versions of the same release on the system
            release_file = "/".join(
                [
                    self.base_storage_location,
                    str(this_user["org_id"]),
                    nbexchange.models.actions.AssignmentActions.released.value,
                    course_code,
                    assignment_code,
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
                handle = open(release_file, "w+b")
                handle.write(file_info["body"])
                handle.close

            except Exception as e:  # TODO: exception handling
                self.log.warning(f"Error: {e}")  # TODO: improve error message

                self.log.info(f"Upload failed")
                # error 500??
                raise Exception

            # now commit the assignment, and get it back to find the id
            assignment = nbexchange.models.assignments.Assignment.find_by_code(
                db=session, code=assignment_code, course_id=course.id
            )

            # Record the notebooks associated with this assignment
            notebooks = self.get_arguments("notebooks")

            for notebook in notebooks:
                new_notebook = nbexchange.models.notebooks.Notebook(name=notebook)
                assignment.notebooks.append(new_notebook)

            # Record the action.
            # Note we record the path to the files.
            self.log.info(
                f"Adding action {nbexchange.models.actions.AssignmentActions.released.value} for user {this_user['id']} against assignment {assignment.id}"
            )
            action = nbexchange.models.actions.Action(
                user_id=this_user["id"],
                assignment_id=assignment.id,
                action=nbexchange.models.actions.AssignmentActions.released,
                location=release_file,
            )
            session.add(action)
        self.finish({"success": True, "note": "Released"})
