import datetime
import os
import time
import uuid

from tornado import httputil, web

from nbexchange.database import scoped_session
from nbexchange.handlers.base import BaseHandler, authenticated
from nbexchange.models.actions import Action, AssignmentActions
from nbexchange.models.assignments import Assignment as AssignmentModel
from nbexchange.models.courses import Course
from nbexchange.models.feedback import Feedback
from nbexchange.models.notebooks import Notebook

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
            note = "Assigment call requires a course id"
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
            course = Course.find_by_code(db=session, code=course_code, org_id=this_user["org_id"], log=self.log)
            if not course:
                note = f"Course {course_code} does not exist"
                self.log.info(note)
                self.finish({"success": False, "note": note, "value": []})
                return

            assignments = AssignmentModel.find_for_course(db=session, course_id=course.id, log=self.log)

            for assignment in assignments:
                self.log.debug("==========")
                self.log.debug(f"Assignment: {assignment}")

                # To maintain backward compatibility we need to test to see if any feedback timestamps match any
                #   submission timestamps. New code will, old code won't.
                # New code matches feedback to submission on timestamp
                # Old code adds latest feedback to all submissions
                # To test old vs new, we check to see if any submit timestamps exist in the set of feedback timestamps
                #   .... if any do, we're new stylee.... and thus _include_ the timestamp in the feedback query.
                feedback_timestamps = set()
                notebook_ids = [notebook.id for notebook in assignment.notebooks]
                submit_timestamps = [
                    action.timestamp
                    for action in assignment.actions
                    if action.action == AssignmentActions.submitted and this_user.get("id") == action.user_id
                ]

                for f in session.query(Feedback).filter(
                    Feedback.notebook_id.in_(notebook_ids), Feedback.timestamp.in_(submit_timestamps)
                ):
                    feedback_timestamps.add(f.timestamp)
                new_stylee = [sub_ts for sub_ts in submit_timestamps if sub_ts in feedback_timestamps]
                # End of new_stylee discovery

                for action in assignment.actions:
                    # For every action that is not "released" checked if the user id matches
                    if action.action != AssignmentActions.released and this_user.get("id") != action.user_id:
                        self.log.debug(f"ormuser: {this_user.get('id')} - actionUser {action.user_id}")
                        self.log.debug("Action does not belong to user, skip action")
                        continue
                    notebooks = []
                    action_timestamp = self.check_timezone(action.timestamp)
                    for notebook in assignment.notebooks:
                        feedback_available = False
                        feedback_timestamp = None
                        if action.action == AssignmentActions.submitted:
                            query_params = {
                                "db": session,
                                "notebook_id": notebook.id,
                                "student_id": this_user.get("id"),
                                "log": self.log,
                            }
                            if new_stylee:
                                query_params["timestamp"] = action_timestamp
                            feedback = Feedback.find_notebook_for_student(**query_params)
                            if feedback:
                                feedback_available = bool(feedback)
                                feedback_timestamp = self.check_timezone(feedback.timestamp).strftime(
                                    self.timestamp_format
                                )
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
                            "timestamp": action_timestamp.strftime(self.timestamp_format),
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

        if course_code not in this_user["courses"]:
            note = f"User not subscribed to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        # Find the course being referred to
        with scoped_session() as session:
            course = Course.find_by_code(db=session, code=course_code, org_id=this_user["org_id"], log=self.log)
            if course is None:
                note = f"Course {course_code} does not exist"
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return  # needs a proper 'fail' here

            note = ""
            self.log.debug(f"Course:{course_code} assignment:{assignment_code}")

            # The location for the data-object is actually held in the 'released' action for the given assignment
            # We want the last one...
            assignment = AssignmentModel.find_by_code(
                db=session,
                code=assignment_code,
                course_id=course.id,
                action=AssignmentActions.released.value,
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

            action = Action.find_most_recent_action(
                db=session,
                assignment_id=assignment.id,
                action=AssignmentActions.released,
                log=self.log,
            )
            release_file = action.location

            if release_file:
                try:
                    # Hmmm this seems to raise it's own 500: No such file or directory if not present
                    with open(release_file, "r+b") as handle:
                        data = handle.read()
                except Exception as e:
                    raise web.HTTPError(500, f"assignment get handler unable to open '{release_file}': {e}")

                self.log.info(
                    f"Adding action {AssignmentActions.fetched.value} for user {this_user['id']} against assignment {assignment.id}"  # noqa: E501
                )
                action = Action(
                    user_id=this_user["id"],
                    assignment_id=assignment.id,
                    action=AssignmentActions.fetched,
                    location=release_file,
                )
                session.add(action)
                self.log.info("record of fetch action committed")
                self.finish(data)
            else:
                raise web.HTTPError(500, f"assignment get handler found no release file {release_file}")

    # This is releasing an **assignment**, not a student submission
    @authenticated
    def post(self):
        # Do a content-length check, before we go any further
        if "Content-Length" in self.request.headers and int(self.request.headers["Content-Length"]) > int(
            self.max_buffer_size
        ):
            note = "File upload oversize, and rejected. Please reduce the contents of the assignment, re-generate, and re-release"  # noqa: E501
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        [course_code, assignment_code] = self.get_params(["course_id", "assignment_id"])
        self.log.debug(
            f"Called POST /assignment with arguments: course {course_code} and  assignment {assignment_code}"
        )
        if not (course_code and assignment_code):
            note = "Posting an Assigment requires a course code and an assignment code"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        this_user = self.nbex_user

        if course_code not in this_user["courses"]:
            note = f"User not subscribed to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        if not "instructor" == this_user["current_role"].casefold():  # we may need to revisit this
            note = f"User not an instructor to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        # The course will exist: the user object creates it if it doesn't exist
        #  - and we know the user is subscribed to the course as an instructor (above)
        with scoped_session() as session:
            course = Course.find_by_code(db=session, code=course_code, org_id=this_user["org_id"], log=self.log)

            # We need to find this assignment, or make a new one.
            assignment = AssignmentModel.find_by_code(db=session, code=assignment_code, course_id=course.id)

            if assignment is None:
                # Look for inactive assignments
                assignment = AssignmentModel.find_by_code(
                    db=session, code=assignment_code, course_id=course.id, active=False
                )

            if assignment is None:
                self.log.info(f"New Assignment details: assignment_code:{assignment_code}, course_id:{course.id}")
                # defaults active
                assignment = AssignmentModel(assignment_code=assignment_code, course_id=course.id)
                session.add(assignment)
                # deliberately no commit: we need to be able to roll-back if there's no data!

            # Set assignment to active
            assignment.active = True

            # storage is dynamically in $path/release/$course_code/$assignment_code/<timestamp>/
            # Note - this means we can have multiple versions of the same release on the system
            release_file = os.path.join(
                self.base_storage_location,
                str(this_user["org_id"]),
                AssignmentActions.released.value,
                course_code,
                assignment_code,
                str(int(time.time())),
            )

            if not self.request.files:
                # self.log.warning("Error: No file supplied in upload")  # TODO: improve error message
                raise web.HTTPError(412, "assignment handler upload: No file supplied in upload")  # precondition failed

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
                raise web.HTTPError(500, f"assignment handler Upload failed: {e}")

            # Check the file exists on disk
            if not (
                os.path.exists(release_file) and os.access(release_file, os.R_OK) and os.path.getsize(release_file) > 0
            ):
                note = "File upload failed."
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return

            # We shouldn't get here, but a double-check is good
            if os.path.getsize(release_file) > self.max_buffer_size:
                os.remove(release_file)
                note = "File upload oversize, and rejected. Please reduce the contents of the assignment, re-generate, and re-release"  # noqa: E501
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return

            # now commit the assignment, and get it back to find the id
            assignment = AssignmentModel.find_by_code(db=session, code=assignment_code, course_id=course.id)

            # Record the notebooks associated with this assignment
            notebooks = self.get_arguments("notebooks")

            for notebook in notebooks:
                self.log.debug(f"Adding notebook {notebook}")
                new_notebook = Notebook(name=notebook)
                assignment.notebooks.append(new_notebook)

            # Record the action.
            # Note we record the path to the files.
            self.log.info(
                f"Adding action {AssignmentActions.released.value} for user {this_user['id']} against assignment {assignment.id}"  # noqa: E501
            )
            timestamp = self.get_timestamp()  # this is a string object
            action = Action(
                user_id=this_user["id"],
                assignment_id=assignment.id,
                action=AssignmentActions.released,
                location=release_file,
                timestamp=datetime.datetime.strptime(
                    timestamp, self.timestamp_format
                ),  # database wants a datetime object
            )
            session.add(action)

            self.finish({"success": True, "note": "Released"})

    # This is unreleasing an assignment
    @authenticated
    def delete(self):
        [course_code, assignment_code, purge] = self.get_params(["course_id", "assignment_id", "purge"])

        self.log.debug(
            f"Called DELETE /assignment with arguments: course {course_code}, assignment {assignment_code}, and purge {purge}"  # noqa: E501
        )
        if not (course_code and assignment_code):
            note = "Unreleasing an Assigment requires a course code and an assignment code"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        this_user = self.nbex_user

        if course_code not in this_user["courses"]:
            note = f"User not subscribed to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        if "instructor" not in map(str.casefold, this_user["courses"][course_code]):
            note = f"User not an instructor to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        note = f"Assignment '{assignment_code}' on course '{course_code}' marked as unreleased"
        with scoped_session() as session:
            course = Course.find_by_code(db=session, code=course_code, org_id=this_user["org_id"], log=self.log)

            assignment = AssignmentModel.find_by_code(db=session, code=assignment_code, course_id=course.id)

            if not assignment:
                note = f"Missing assignment for {assignment_code} and {course_code}, cannot delete"
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return

            # Set assignment to inactive
            assignment.active = False
            # Delete the associated notebook
            for notebook in assignment.notebooks:
                session.delete(notebook)

            # If we have the purge parameter, we actually delete the data
            # The various 'cascade on delete' settings should clear all the sub-tables
            if purge:
                session.delete(assignment)
                note = f"Assignment '{assignment_code}' on course '{course_code}' deleted and purged from the database"
        self.log.info(f"{note} by user {this_user['id']} ")
        self.finish({"success": True, "note": note})
