import base64
import os
import tempfile
import time

from dateutil import parser
from tornado import web

from nbexchange.database import scoped_session
from nbexchange.handlers.base import BaseHandler, authenticated
from nbexchange.models.actions import Action, AssignmentActions
from nbexchange.models.assignments import Assignment as AssignmentModel
from nbexchange.models.courses import Course
from nbexchange.models.feedback import Feedback
from nbexchange.models.notebooks import Notebook
from nbexchange.models.users import User

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
            course = Course.find_by_code(db=session, code=course_id, org_id=this_user["org_id"], log=self.log)
            if not course:
                note = f"Course {course_id} not found"
                self.log.info(note)
                # self.finish({"success": False, "note": note, "value": []})
                # return
                raise web.HTTPError(404, note)

            assignment = AssignmentModel.find_by_code(db=session, code=assignment_id, course_id=course.id, log=self.log)
            if not assignment:
                note = f"Assignment {assignment_id} for Course {course_id} not found"
                self.log.info(note)
                # self.finish({"success": False, "note": note, "value": []})
                # return
                raise web.HTTPError(404, note)

            student = User.find_by_name(db=session, name=this_user["name"], log=self.log)

            res = Feedback.find_all_for_student(
                db=session,
                student_id=student.id,
                assignment_id=assignment.id,
                log=self.log,
            )
            feedbacks = []
            for r in res:
                f = {}
                notebook = Notebook.find_by_pk(db=session, pk=r.notebook_id, log=self.log)
                if notebook is not None:
                    feedback_name = "{0}.html".format(notebook.name)
                else:
                    feedback_name = os.path.basename(r.location)
                with open(r.location, "r+b") as fp:
                    f["content"] = base64.b64encode(fp.read()).decode("utf-8")
                f["filename"] = feedback_name

                # This matches self.timestamp_format
                f["timestamp"] = self.check_timezone(r.timestamp).strftime(self.timestamp_format)
                f["checksum"] = r.checksum
                feedbacks.append(f)

                # Add action
                self.log.info(
                    f"Adding action {AssignmentActions.feedback_fetched.value} by user {this_user['id']} against assignment {assignment.id}"  # noqa: E501
                )
                action = Action(
                    user_id=this_user["id"],
                    assignment_id=assignment.id,
                    action=AssignmentActions.feedback_fetched,
                    location=r.location,
                )
                session.add(action)
            self.finish({"success": True, "feedback": feedbacks})

    @authenticated
    def post(self) -> None:
        """
        This endpoint accepts feedback files for a notebook.
        Parameters:

        course_id: course_code [eg 'Made up`]
        assignment_id: assignment code [eg 'Lab 1 final test'],
        student_id: the "username" of the student [eg '1-ug241234'],
        notebook_id: the name of the notebook without the extension [eg 'Main test'],
        timestamp: the timestap for the submission that this feedback belongs to [eg '2025-01-17 15:17:58.447679 UTC']

        [checksum: not used]

        The endpoint return {'success': true} for all successful feedback releases.
        """

        [course_id, assignment_id, notebook_id, student_id, timestamp, checksum] = self.get_params(
            [
                "course_id",
                "assignment_id",
                "notebook",
                "student",
                "timestamp",
                "checksum",
            ]
        )

        if not (course_id and assignment_id and notebook_id and student_id and timestamp and checksum):
            note = (
                "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."
            )
            self.log.debug(note)
            self.finish({"success": False, "note": note})
            return

        this_user = self.nbex_user

        if course_id not in this_user["courses"]:
            note = f"User not subscribed to course {course_id}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        if "instructor" != this_user["current_role"].casefold():  # we may need to revisit this
            note = f"User not an instructor to course {course_id}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        with scoped_session() as session:
            # Start building feedback object

            course = Course.find_by_code(db=session, code=course_id, org_id=this_user["org_id"], log=self.log)

            if not course:
                self.log.info(f"Could not find requested resource course {course_id}")
                raise web.HTTPError(404, f"Could not find requested resource course {course_id}")

            assignment = AssignmentModel.find_by_code(
                db=session,
                code=assignment_id,
                course_id=course.id,
                action=AssignmentActions.released.value,
            )

            if not assignment:
                note = f"Could not find requested resource assignment {assignment_id}"
                self.log.info(note)
                raise web.HTTPError(404, note)

            notebook = Notebook.find_by_name(db=session, name=notebook_id, assignment_id=assignment.id, log=self.log)
            if not notebook:
                note = f"Could not find requested resource notebook {notebook_id}"
                self.log.info(note)
                raise web.HTTPError(404, note)

            student = User.find_by_name(db=session, name=student_id, log=self.log)

            if not student:
                note = f"Could not find requested resource student {student_id}"
                self.log.info(note)
                raise web.HTTPError(404, note)

            # Check whether there is an HTML file attached to the request
            if not self.request.files:
                self.log.warning("Error: No file supplied in upload")  # TODO: improve error message
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

            location = os.path.join(
                self.base_storage_location,
                str(this_user["org_id"]),
                "feedback",
                notebook.assignment.course.course_code,
                notebook.assignment.assignment_code,
                str(int(time.time())),
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

            # convert to datetime object & ensure it's got a timezone
            timestamp = self.check_timezone(parser.parse(timestamp))  #
            feedback = Feedback(
                notebook_id=notebook.id,
                checksum=checksum,
                location=feedback_file,
                student_id=student.id,
                instructor_id=this_user.get("id"),
                timestamp=timestamp,
            )

            session.add(feedback)

            # Add action
            self.log.info(
                f"Adding action {AssignmentActions.feedback_released.value} by user {this_user['id']}, for student {student.id}, against assignment {assignment.id}"  # noqa: E501
            )
            action = Action(
                user_id=this_user["id"],
                assignment_id=notebook.assignment.id,
                action=AssignmentActions.feedback_released,
                location=feedback_file,
            )
            session.add(action)

        self.finish({"success": True, "note": "Feedback released"})
