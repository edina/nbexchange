import datetime
import os
import re
import time
import uuid

from dateutil.tz import gettz
from nbexchange import orm
from nbexchange.base import BaseHandler
from tornado import web
from urllib.parse import quote_plus, unquote, unquote_plus
from urllib.request import urlopen

"""
All URLs relative to /services/nbexchange

Submission calls:
.../submissions?course_id=$course_code
GET: gets list of users who've submitted so far

.../submission?course_id=$course_code&assignment_id=$assignment_code
GET: gets the assignment for that user [Instructor only]
POST (with data) stores the submission for that user

This relys on users being logged in, and the user-object having additional data:
'role' (as per LTI)
"""


class Submission(BaseHandler):
    """.../submisssion/
parmas:
    course_id: course_code
    assignment_id: assignment_code

[? GET: (role=instructor) collects an assignment ?]
POST: (with file) submits an assignment
"""

    urls = ["submission"]

    # This is a student submitting an assignment, not an instructor "release"
    @web.authenticated
    def post(self):

        [course_code, assignment_code] = self.get_params(["course_id", "assignment_id"])

        if not course_code and not assignment_code:
            self.log.info(
                f"Assigment call requires both a course code and an assignment code!!"
            )
            return

        this_user = self.nbex_user

        if not course_code in this_user["courses"]:
            note = f"User not subscribed to course {course_code}"
            self.log.info(note)
            self.write({"success": False, "note": note})
            return

        # The course will exist: the user object creates it if it doesn't exist
        #  - and we know the user is subscribed to the course as an instructor (above)
        course = orm.Course.find_by_code(
            db=self.db, code=course_code, org_id=this_user["org_id"], log=self.log
        )

        # We need to find this assignment, or make a new one.
        assignment = orm.Assignment.find_by_code(
            db=self.db, code=assignment_code, course_id=course.id
        )
        if assignment is None:
            note = f"User not fetched assignment {assignment_code}"
            self.log.info(note)
            self.write({"success": False, "note": note})
            return

        # storage is dynamically in $path/submitted/$course_code/$assignment_code/$username/<timestamp>/
        # Note - this means that a user can submit multiple times, and we have all copies
        release_file = "/".join(
            [
                self.base_storage_location,
                "submitted",
                course_code,
                assignment_code,
                this_user["name"],
                str(int(time.time())),
            ]
        )

        try:
            # Write the uploaded file to the desired location
            file_info = self.request.files["assignment"][0]

            filename, content_type = file_info["filename"], file_info["content_type"]
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
            self.db.rollback()
            # error 500??
            raise Exception

        # now commit the assignment, and get it back to find the id
        self.db.commit()
        assignment = orm.Assignment.find_by_code(
            db=self.db, code=assignment_code, course_id=course.id
        )

        # Record the action.
        # Note we record the path to the files.
        self.log.info(
            f"!!!!!!!!!!!!!! submission details for upload:{assignment.id}|{assignment.course_id}"
        )
        action = orm.Action(
            user_id=this_user["ormUser"].id,
            assignment_id=assignment.id,
            action=orm.AssignmentActions.submitted,
            location=release_file,
        )
        self.db.add(action)
        self.db.commit()
        self.write({"success": True, "note": "Released"})


class Submissions(BaseHandler):
    urls = ["submissions"]

    @web.authenticated
    def post(self):

        self.write(f"##### I received a POST for /submissions")
