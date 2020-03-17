import os
import tempfile
import time
import uuid

from sqlalchemy import desc
from tornado import web, httputil

import nbexchange.models.actions
import nbexchange.models.assignments
import nbexchange.models.courses
import nbexchange.models.notebooks
import nbexchange.models.feedback
from nbexchange.database import scoped_session
from nbexchange.handlers.base import BaseHandler, authenticated
from nbgrader.utils import notebook_hash, make_unique_key

"""
All URLs relative to /services/nbexchange

This relys on users being logged in, and the user-object having additional data:
'role' (as per LTI)
"""


class FeedbackHandler(BaseHandler):
    """.../feedback/
    parmas:
        course_id: course_code
        assignment_id: assignment_code
        user_id: user_id (optional)

    GET: Get list of feedback files for an assignment and user
    POST: (role=instructor, with file): Add ("feedback") to an assignment
    """

    urls = ["feedback"]

    # Fetch feedback
    @authenticated
    def get(self):

        [notebook_id] = self.get_params(["notebook_id"])

        if not notebook_id:
            note = "Feedback call requires a notebook id."
            self.log.debug(note)
            self.finish({"success": False, "note": note})
            return

        self.log.debug(f"Notebook ID: {notebook_id}")
        this_user = self.nbex_user

        with scoped_session() as session:
            notebook = (
                session.query(nbexchange.models.notebooks.Notebook)
                .filter_by(id=notebook_id)
                .first()
            )
            self.log.info(notebook)
            self.log.debug(this_user)

            if not notebook:
                raise web.HTTPError(404, "Could not find requested resource")

            # Find feedback for this notebook
            res = (
                session.query(nbexchange.models.feedback.Feedback)
                .filter_by(notebook_id=notebook_id)
                .first()
            )

            self.finish({"success": True, "feedback": str(res)})

    @authenticated
    def post(self):
        """
        This endpoint accepts feedback files for a notebook.
        It requires a notebook id, student id, feedback timestamp and
        a checksum.

        The endpoint return {'success': true} for all successful feedback releases.
        """

        [course_id, assignment_id, notebook, student, timestamp, checksum] = self.get_params(
            ["course_id", "assignment_id", "notebook", "student", "timestamp", "checksum"]
        )

        if not (course_id and assignment_id and notebook and student and timestamp and checksum):
            note = "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."
            self.log.debug(note)
            self.finish({"success": False, "note": note})
            return

        this_user = self.nbex_user

        with scoped_session() as session:

            # Start building feedback object

            # TODO: Recalculate checksum and check
            # unique_key = make_unique_key(
            #     course_id,
            #     assignment_id,
            #     notebook,
            #     student,
            #     str(timestamp).strip(),
            # )

            course = nbexchange.models.courses.Course.find_by_code(
                db=session, code=course_id, org_id=this_user["org_id"], log=self.log
            )

            if not course:
                raise web.HTTPError(404, "Could not find requested resource")

            assignment = (
                session.query(nbexchange.models.assignments.Assignment)
                .filter_by(assignment_code=assignment_id, course_id=course.id)
                .first()
            )

            if not assignment:
                raise web.HTTPError(404, "Could not find requested resource")

            notebook = (
                session.query(nbexchange.models.notebooks.Notebook)
                .filter_by(name=notebook, assignment_id=assignment.id)
                .first()
            )

            if not notebook:
                raise web.HTTPError(404, "Could not find requested resource")

            student = (
                session.query(nbexchange.models.users.User)
                .filter_by(name=student)
                .first()
            )

            if not student:
                raise web.HTTPError(404, "Could not find requested resource")

            # raise Exception(f"{res}")
            self.log.info("Notebook", notebook)
            self.log.info("Student", student)
            self.log.info("Instructor", this_user)

            # TODO: check access. Is the user an instructor on the course to which the notebook belongs

            # Check whether there is an HTML file attached to the request
            if not self.request.files:
                self.log.warning(
                    f"Error: No file supplies in upload"
                )  # TODO: improve error message
                raise web.HTTPError(412)  # precondition failed

            try:
                # Grab the file
                file_info = self.request.files["feedback"][0]
                filename, content_type = (
                    file_info["filename"],
                    file_info["content_type"],
                )
                note = f"Received file {filename}, of type {content_type}"
                self.log.info(note)
                fbfile = tempfile.NamedTemporaryFile()
                fbfile.write(file_info["body"])
                fbfile.seek(0)
            except Exception:
                # Could not grab the feedback file
                raise web.HTTPError(412)


            # TODO: What is file of the original notebook we are getting the feedback for?
            # assignment_dir = "collected/student_id/assignment_name"
            # nbfile = os.path.join(assignment_dir, "{}.ipynb".format(notebook.name))
            # calc_checksum = notebook_hash(nbfile.name, unique_key)
            # if calc_checksum != checksum:
            #     self.log.info(f"Mismatched checksums {calc_checksum} and {checksum}.")
            #     raise web.HTTPError(412)

            location = "/".join(
                [
                    self.base_storage_location,
                    str(this_user["org_id"]),
                    "feedback",
                    notebook.assignment.course.course_code,
                    notebook.assignment.assignment_code,
                    str(int(time.time())),
                ]
            )

            # This should be abstracted, so it can be overloaded to store in other manners (eg AWS)
            feedback_file = location + "/" + checksum + ".html"

            try:
                # Ensure the directory exists
                os.makedirs(os.path.dirname(feedback_file), exist_ok=True)
                handle = open(feedback_file, "w+b")
                handle.write(file_info["body"])
                handle.close()
            except Exception as e:
                self.log.error(f"Could not save file. \n {e}")
                raise web.HTTPError(500)

            feedback = nbexchange.models.feedback.Feedback(
                notebook_id=notebook.id,
                checksum=checksum,
                location=feedback_file,
                student_id=student.id,
                instructor_id=this_user.get("id"),
                timestamp=timestamp,
            )

            session.add(feedback)

        self.finish({"success": True, "note": "Feedback released"})
