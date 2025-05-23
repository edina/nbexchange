import os
import uuid

from dateutil import parser
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
        course_id: course_code [eg 'cool course']
        assignment_id: assignment_code [eg 'Indivisual Assessment 1']
        timestamp: The timestamp in timestamp.txt [eg '2020-01-01 00:00:00.0 UTC']

    POST: (with file) submits an assignment"""

    urls = ["submission"]

    # This has no authentiction wrapper, so false implication os service
    def get(self):
        raise web.HTTPError(501)

    # This is a student submitting an assignment, not an instructor "release"
    @authenticated
    def post(self):
        # if "Content-Length" in self.request.headers and int(self.request.headers["Content-Length"]) > int(
        #     self.max_buffer_size
        # ):
        #     note = "File upload oversize, and rejected. Please reduce the files in your submission and try again."
        #     self.log.info(note)
        #     self.finish({"success": False, "note": note})
        #     return

        [course_code, assignment_code, timestamp] = self.get_params(["course_id", "assignment_id", "timestamp"])
        self.log.debug(
            f"Called POST /submission with arguments: course {course_code} and ",
            f"assignment {assignment_code}, giving a timestamp of {timestamp}",
        )
        if not (course_code and assignment_code):
            note = "Submission call requires a course code and an assignment code"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        # If this happens, then any feedback isn't going to sync with this submission
        if not timestamp:
            timestamp = self.get_timestamp()
            note = f"Submission was posted without a timestamp. We've set it to {timestamp}, but feedback will not sync to this."  # noqa: E501
            self.log.info(note)

        this_user = self.nbex_user

        if course_code not in this_user["courses"]:
            note = f"User not subscribed to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        # The course will exist: the user object creates it if it doesn't exist
        #  - and we know the user is subscribed to the course as an instructor (above)
        with scoped_session() as session:
            course = Course.find_by_code(db=session, code=course_code, org_id=this_user["org_id"], log=self.log)

            # We need to find this assignment, or make a new one.
            assignment = Assignment.find_by_code(db=session, code=assignment_code, course_id=course.id)
            if assignment is None:
                note = f"User not fetched assignment {assignment_code}"
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return

            # validate timestamp: convert to datetime object & ensure it's got a timezone
            timestamp = self.check_timezone(parser.parse(timestamp))

            # storage is dynamically in $path/submitted/$course_code/$assignment_code/$username/<timestamp>/
            # Note - this means that a user can submit multiple times, and we have all copies
            release_file = os.path.join(
                self.base_storage_location,
                str(this_user["org_id"]),
                AssignmentActions.submitted.value,
                course_code,
                assignment_code,
                this_user["name"],
                str(int(timestamp.timestamp())),  # this is a daterime rendition (eg '1738054326')
            )

            if not self.request.files:
                raise web.HTTPError(412, "submission handler post: No file supplied in upload")  # precondition failed

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

                # Hmmm this seems to raise it's own 500: No such file or directory if not present
                with open(release_file, "w+b") as handle:
                    handle.write(file_info["body"])

            except Exception as e:  # TODO: exception handling
                raise web.HTTPError(500, f"submission handler Upload failed: {e}")

            # Check the file exists on disk
            if not (
                os.path.exists(release_file) and os.access(release_file, os.R_OK) and os.path.getsize(release_file) > 0
            ):
                note = "File upload failed."
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return

            # We shouldn't need this, but it's good to double-check
            if os.path.getsize(release_file) > self.max_buffer_size:
                os.remove(release_file)
                note = "File upload oversize, and rejected. Please reduce the files in your submission and try again."
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return

            # now commit the assignment, and get it back to find the id
            assignment = Assignment.find_by_code(db=session, code=assignment_code, course_id=course.id)

            # Record the action.
            # Note we record the path to the files.
            self.log.info(
                f"Adding action {AssignmentActions.submitted.value} for user {this_user['id']} against assignment {assignment.id} at time {timestamp}"  # noqa: E501
            )

            # The action timestamp _must_ be the same value as in the timestamp.txt file in the submission
            action = Action(
                user_id=this_user["id"],
                assignment_id=assignment.id,
                action=AssignmentActions.submitted,
                location=release_file,
                timestamp=timestamp,
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
