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


class Assignments(BaseHandler):
    """.../assignments/
    parmas:
        course_id: course_code

    GET: gets list of assignments for $course_code
    """

    urls = ["assignments"]

    @authenticated
    def get(self):

        models = []

        [course_code] = self.get_params(["course_id"])

        if not course_code:
            note = f"Assigment call requires a course id"
            self.log.info(note)
            self.finish({"success": False, "note": note, "value": []})
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
            self.finish({"success": False, "note": note, "value": []})
            return

        # Find the course being referred to
        with scoped_session() as session:
            course = nbexchange.models.courses.Course.find_by_code(
                db=session, code=course_code, org_id=this_user["org_id"], log=self.log
            )
            if not course:
                note = f"Course {course_code} does not exist"
                self.log.info(note)
                self.finish({"success": False, "note": note, "value": []})
                return

            assignments = nbexchange.models.assignments.Assignment.find_for_course(
                db=session, course_id=course.id, log=self.log
            )

            for assignment in assignments:
                self.log.debug(f"==========")
                self.log.debug(f"Assignment: {assignment}")
                for action in assignment.actions:
                    # For every action that is not "released" checked if the user id matches
                    if (
                        action.action
                        != nbexchange.models.actions.AssignmentActions.released
                        and this_user.get("id") != action.user_id
                    ):
                        self.log.debug(
                            f"ormuser: {this_user.get('id')} - actionUser {action.user_id}"
                        )
                        self.log.debug("Action does not belong to user, skip action")
                        continue
                    notebooks = []

                    for notebook in assignment.notebooks:

                        if (
                            action.action
                            == nbexchange.models.actions.AssignmentActions.submitted
                        ):
                            feedback = (
                                session.query(nbexchange.models.feedback.Feedback)
                                .filter_by(
                                    notebook_id=notebook.id,
                                    student_id=this_user.get("id"),
                                )
                                .first()
                            )
                            feedback_available = bool(feedback)
                            feedback_timestamp = (
                                feedback.timestamp.isoformat(" ")
                                if feedback_available
                                else None
                            )

                        else:
                            feedback_available = False
                            feedback_timestamp = None

                        notebooks.append(
                            {
                                "notebook_id": notebook.name,
                                "has_exchange_feedback": feedback_available,
                                "feedback_updated": False,  # TODO: needs a real value
                                "feedback_timestamp": feedback_timestamp,
                            }
                        )
                    models.append(
                        {
                            "assignment_id": assignment.assignment_code,
                            "student_id": action.user_id,
                            "course_id": assignment.course.course_code,
                            "status": action.action.value,  # currently called 'action' in our db
                            "path": action.location,
                            "notebooks": notebooks,
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


class Assignment(BaseHandler):
    """.../assignment/
    parmas:
        course_id: course_code
        assignment_id: assignment_code

    GET: downloads assignment
    POST: (role=instructor, with file): Add ("release") an assignment
    """

    # urls = ["assignment/([^/]+)(?:/?([^/]+))?"]
    urls = ["assignment"]

    @authenticated
    def get(self):  # def get(self, course_code, assignment_code=None):

        [course_code, assignment_code] = self.get_params(["course_id", "assignment_id"])

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
            course = nbexchange.models.courses.Course.find_by_code(
                db=session, code=course_code, org_id=this_user["org_id"], log=self.log
            )
            if course is None:
                note = f"Course {course_code} does not exist"
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return  # needs a proper 'fail' here

            note = ""
            self.log.debug(f"Course:{course_code} assignment:{assignment_code}")

            # The location for the data-object is actually held in the 'released' action for the given assignment
            # We want the last one...
            assignment = nbexchange.models.assignments.Assignment.find_by_code(
                db=session,
                code=assignment_code,
                course_id=course.id,
                action=nbexchange.models.actions.AssignmentActions.released.value,
            )

            if assignment is None:
                note = f"Assignment {assignment_code} does not exist"
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return  # needs a proper 'fail' here

            self._headers = httputil.HTTPHeaders(
                {
                    "Content-Type": "application/gzip",
                    "Date": httputil.format_timestamp(time.time()),
                }
            )

            data = b""

            release_file = None

            # Find the most recent released action for this assignment
            action = (
                session.query(nbexchange.models.actions.Action)
                .filter_by(assignment_id=assignment.id)
                .filter_by(action=nbexchange.models.actions.AssignmentActions.released)
                .order_by(desc(nbexchange.models.actions.Action.id))
                .first()
            )
            release_file = action.location

            if release_file:
                try:
                    handle = open(release_file, "r+b")
                    data = handle.read()
                    handle.close()
                except Exception as e:  # TODO: exception handling
                    self.log.warning(f"Error: {e}")  # TODO: improve error message
                    self.log.info(f"Unable to open file")

                    # error 500??
                    raise Exception

                self.log.info(
                    f"Adding action {nbexchange.models.actions.AssignmentActions.fetched.value} for user {this_user['id']} against assignment {assignment.id}"
                )
                action = nbexchange.models.actions.Action(
                    user_id=this_user["id"],
                    assignment_id=assignment.id,
                    action=nbexchange.models.actions.AssignmentActions.fetched,
                    location=release_file,
                )
                session.add(action)
                self.log.info("record of fetch action committed")
                self.finish(data)
            else:
                self.log.info("no release file found")
                raise Exception

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
                handle.close()

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
                self.log.error(f"Adding notebook {notebook}")
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

    # This is unreleasing an assignment
    @authenticated
    def delete(self):

        [course_code, assignment_code] = self.get_params(["course_id", "assignment_id"])

        self.log.debug(
            f"Called DELETE /assignment with arguments: course {course_code} and  assignment {assignment_code}"
        )
        if not (course_code and assignment_code):
            note = f"Unreleasing an Assigment requires a course code and an assignment code"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        this_user = self.nbex_user

        if not course_code in this_user["courses"]:
            note = f"User not subscribed to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return
        if not "instructor" in map(str.casefold, this_user["courses"][course_code]):
            note = f"User not an instructor to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        with scoped_session() as session:
            course = nbexchange.models.courses.Course.find_by_code(
                db=session, code=course_code, org_id=this_user["org_id"], log=self.log
            )

            assignment = nbexchange.models.assignments.Assignment.find_by_code(
                db=session, code=assignment_code, course_id=course.id
            )

            # Set assignment to inactive
            assignment.active = False
            # Delete the associated notebook
            for notebook in assignment.notebooks:
                session.delete(notebook)

        self.finish({"success": True, "note": "Assignment deleted"})
