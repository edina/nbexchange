import base64
import os
import time
import uuid

from dateutil import parser
from sqlalchemy import func
from tornado import web

from nbexchange.database import scoped_session
from nbexchange.feedback_revision import read_feedback_revision
from nbexchange.grade_events import record_grade_ready_event
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
                raise web.HTTPError(404, note)

            assignment = AssignmentModel.find_by_code(db=session, code=assignment_id, course_id=course.id, log=self.log)
            if not assignment:
                note = f"Assignment {assignment_id} for Course {course_id} not found"
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
                raise web.HTTPError(404, f"Could not find requested resource course {course_id}")

            assignment = AssignmentModel.find_by_code(
                db=session,
                code=assignment_id,
                course_id=course.id,
                action=AssignmentActions.released.value,
            )

            if not assignment:
                raise web.HTTPError(404, f"Could not find requested resource assignment {assignment_id}")

            notebook = Notebook.find_by_name(db=session, name=notebook_id, assignment_id=assignment.id, log=self.log)
            if not notebook:
                raise web.HTTPError(404, f"Could not find requested resource notebook {notebook_id}")

            student = User.find_by_name(db=session, name=student_id, log=self.log)

            if not student or student.org_id != course.org_id:
                raise web.HTTPError(404, f"Could not find requested resource student {student_id}")

            try:
                body = self.request.files["feedback"][0]["body"]
            except (IndexError, KeyError) as exc:
                raise web.HTTPError(412, "No feedback file supplied") from exc

            notebooks = {item.name for item in Notebook.find_all_for_assignment(session, assignment.id)}
            notebook_pk = notebook.id
            identity = {
                "organisation_id": course.org_id,
                "course": {"id": course.id, "code": course.course_code},
                "assignment": {"id": assignment.id, "code": assignment.assignment_code},
                "learner": {"id": student.id, "name": student.name},
            }

        timestamp = self.check_timezone(parser.parse(timestamp))
        revision, released_grade = read_feedback_revision(
            body,
            course=course_id,
            assignment=assignment_id,
            learner=student_id,
            notebook=notebook_id,
            timestamp=timestamp,
            notebooks=notebooks,
        )

        location = os.path.join(
            self.base_storage_location,
            str(identity["organisation_id"]),
            "feedback",
            identity["course"]["code"],
            identity["assignment"]["code"],
            str(int(time.time())),
        )
        feedback_file = os.path.join(location, f"{uuid.uuid4().hex}.html")

        try:
            os.makedirs(os.path.dirname(feedback_file), exist_ok=True)
            with open(feedback_file, "w+b") as handle:
                handle.write(body)
        except OSError as exc:
            raise web.HTTPError(500, f"Could not save file. \n {exc}") from exc

        with scoped_session() as session:
            # Serialize uploads for this learner. The file is already written,
            # and the feedback row and any resulting event commit together.
            learner_pk = identity["learner"]["id"]
            session.query(User.id).filter_by(id=learner_pk).with_for_update().one()
            previous = Feedback.find_notebook_for_student(session, notebook_pk, learner_pk, timestamp)
            feedback = Feedback(
                notebook_id=notebook_pk,
                checksum=checksum,
                location=feedback_file,
                student_id=identity["learner"]["id"],
                instructor_id=this_user.get("id"),
                timestamp=timestamp,
                grade_revision=revision,
            )

            session.add(feedback)

            # Add action
            self.log.info(
                "Released feedback for student %s on assignment %s",
                identity["learner"]["id"],
                identity["assignment"]["id"],
            )
            action = Action(
                user_id=this_user["id"],
                assignment_id=identity["assignment"]["id"],
                action=AssignmentActions.feedback_released,
                location=feedback_file,
            )
            session.add(action)
            if revision is None:
                released_grade = {"grade_state": "unavailable", "grade": None}
            elif previous is not None and previous.grade_revision == revision:
                released_grade = None
            else:
                latest_feedback = (
                    session.query(func.max(Feedback.id))
                    .join(Notebook)
                    .filter(
                        Notebook.assignment_id == identity["assignment"]["id"],
                        Feedback.student_id == learner_pk,
                        Feedback.timestamp == timestamp,
                    )
                    .group_by(Feedback.notebook_id)
                )
                matching = (
                    session.query(Feedback)
                    .filter(
                        Feedback.id.in_(latest_feedback),
                        Feedback.grade_revision == revision,
                    )
                    .count()
                )
                if matching != len(notebooks):
                    released_grade = None

            if released_grade is not None:
                record_grade_ready_event(session, action=action, identity=identity, released_grade=released_grade)

        self.finish({"success": True, "note": "Feedback released"})
