import base64
import datetime
import os
import tempfile
import time
import uuid

from sqlalchemy import desc
from tornado import web, httputil
from dateutil import parser

from nbexchange.models.actions import Action, AssignmentActions
from nbexchange.models.assignments import Assignment
from nbexchange.models.courses import Course
from nbexchange.models.notebooks import Notebook
from nbexchange.models.feedback import Feedback
from nbexchange.models.users import User
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

        [course_id, assignment_id] = self.get_params(["course_id", "assignment_id"])

        if not assignment_id or not course_id:
            note = "Feedback call requires an assignment id and a course id"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        self.log.debug(f"checking for feedback for {assignment_id} on {course_id}")

        this_user = self.nbex_user

        with scoped_session() as session:

            assignment = (
                session.query(Assignment)
                .join(Course)
                .filter(Assignment.assignment_code==assignment_id)
                .filter(Assignment.active==True)
                .filter(Course.course_code==course_id)
                .filter(Course.org_id==this_user["org_id"])
                .order_by(Assignment.id.desc())
                .first()
            )

            if not assignment:
                raise web.HTTPError(404, "Could not find requested resource")

            student = (
                session.query(User)
                .filter_by(name=this_user["name"])
                .first()
            )

            # Find feedback for this notebook
            res = (
                session.query(Feedback)
                .join(Notebook)
                .filter(Feedback.student_id==student.id)
                .filter(Notebook.assignment_id==assignment.id)
                .all()
            )
            feedbacks = []
            for r in res:
                f = {}
                notebook = (
                    session.query(Notebook)
                    .filter_by(id=r.notebook_id)
                    .first()
                )
                if notebook is not None:
                    feedback_name = "{0}.html".format(notebook.name)
                else:
                    feedback_name = os.path.basename(r.location)
                with open(r.location, "r+b") as fp:
                    f["content"] = base64.b64encode(fp.read()).decode("utf-8")
                f["filename"] = feedback_name
                # This matches self.timestamp_format
                f["timestamp"] = r.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f %Z")
                f["checksum"] = r.checksum
                feedbacks.append(f)

                # Add action
                action = Action(
                    user_id=this_user["id"],
                    assignment_id=assignment.id,
                    action=AssignmentActions.feedback_fetched,
                    location=r.location,
                )
                session.add(action)
            self.finish({"success": True, "feedback": feedbacks})

    @authenticated
    def post(self):
        """
        This endpoint accepts feedback files for a notebook.
        It requires a notebook id, student id, feedback timestamp and
        a checksum.

        The endpoint return {'success': true} for all successful feedback releases.
        """

        [
            course_id,
            assignment_id,
            notebook_id,
            student_id,
            timestamp,
            checksum,
        ] = self.get_params(
            [
                "course_id",
                "assignment_id",
                "notebook",
                "student",
                "timestamp",
                "checksum",
            ]
        )

        if not (
            course_id
            and assignment_id
            and notebook_id
            and student_id
            and timestamp
            and checksum
        ):
            note = "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."
            self.log.debug(note)
            self.finish({"success": False, "note": note})
            return

        this_user = self.nbex_user
        if course_id not in this_user["courses"]:
            note = f"User not subscribed to course {course_id}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        if (
            "instructor" != this_user["current_role"].casefold()
        ):  # we may need to revisit this
            note = f"User not an instructor to course {course_id}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        with scoped_session() as session:

            # Start building feedback object

            course = Course.find_by_code(
                db=session, code=course_id, org_id=this_user["org_id"], log=self.log
            )

            if not course:
                self.log.info(f"Could not find requested resource course {course_id}")
                raise web.HTTPError(
                    404, f"Could not find requested resource course {course_id}"
                )

            assignment = (
                session.query(Assignment)
                .filter_by(assignment_code=assignment_id, course_id=course.id)
                .first()
            )

            if not assignment:
                self.log.info(
                    f"Could not find requested resource assignment {assignment_id}"
                )
                raise web.HTTPError(
                    404, f"Could not find requested resource assignment {assignment_id}"
                )

            notebook = (
                session.query(Notebook)
                .filter_by(name=notebook_id, assignment_id=assignment.id)
                .first()
            )

            if not notebook:
                self.log.info(
                    f"Could not find requested resource notebook {notebook_id}"
                )
                raise web.HTTPError(
                    404, f"Could not find requested resource notebook {notebook_id}"
                )

            student = (
                session.query(User)
                .filter_by(name=student_id)
                .first()
            )

            if not student:
                self.log.info(f"Could not find requested resource student {student_id}")
                raise web.HTTPError(
                    404, f"Could not find requested resource student {student_id}"
                )

            # # raise Exception(f"{res}")
            # self.log.info(f"Notebook: {notebook}")
            # self.log.info(f"Student: {student}")
            # self.log.info(f"Instructor: {this_user}")

            # TODO: check access. Is the user an instructor on the course to which the notebook belongs

            # Check whether there is an HTML file attached to the request
            if not self.request.files:
                self.log.warning(
                    f"Error: No file supplied in upload"
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

            except Exception as e:
                # Could not grab the feedback file
                self.log.error(f"Error: {e}")
                raise web.HTTPError(412)
            # TODO: should we check the checksum?
            # unique_key = make_unique_key(
            #     course_id,
            #     assignment_id,
            #     notebook_id,
            #     student_id,
            #     str(timestamp).strip(),
            # )
            # check_checksum = notebook_hash(fbfile.name, unique_key)
            #
            # if check_checksum != checksum:
            #     self.log.info(f"Checksum {checksum} does not match {check_checksum}")
            #     raise web.HTTPError(403, f"Checksum {checksum} does not match {check_checksum}")

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
                with open(feedback_file, "w+b") as handle:
                    handle.write(file_info["body"])
            except Exception as e:
                self.log.error(f"Could not save file. \n {e}")
                raise web.HTTPError(500)

            feedback = Feedback(
                notebook_id=notebook.id,
                checksum=checksum,
                location=feedback_file,
                student_id=student.id,
                instructor_id=this_user.get("id"),
                timestamp=parser.parse(timestamp),
            )

            session.add(feedback)

            # Add action
            action = Action(
                user_id=this_user["id"],
                assignment_id=notebook.assignment.id,
                action=AssignmentActions.feedback_released,
                location=feedback_file,
            )
            session.add(action)

        self.finish({"success": True, "note": "Feedback released"})
