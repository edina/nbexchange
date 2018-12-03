import datetime
import json
import os
import random
import re
import time
import uuid

from dateutil.tz import gettz

from nbexchange import orm
from nbexchange.base import BaseHandler

from tornado import web, httputil
from urllib.parse import quote_plus, unquote, unquote_plus
from urllib.request import urlopen

"""
All URLs relative to /services/nbexchange

Assinments calls:
.../assignments?course_id=$course_code
GET: returns list of assignments

Assignment calls:
.../assignment?course_id=$course_code[&assignment_id=$assignment_code]

GET: Downloads that assignment
POST Upload that assignment

This relys on users being logged in, and the user-object having additional data:
'role' (as per LTI)
"""


class Assignments(BaseHandler):
    """.../assignments/
parmas:
    course_id: course_code

GET: (without assignment_code) gets list of assignments for $course_code
"""

    urls = ["assignments"]

    @web.authenticated
    def get(self):
        self.log.debug("+++++ assignment GET starting")

        params = self.request.arguments
        self.log.debug("params:{}".format(params))
        course_code = (
            self.request.arguments["course_id"][0].decode("utf-8")
            if "course_id" in self.request.arguments
            else None
        )

        models = []

        if not course_code:
            note = "Assigment call requires both a course code"
            self.log.info(note)
            self.write({"success": False, "value": models, "note": note})

        # Un url-encode variables
        course_code = (
            unquote(course_code)
            if re.search("%20", course_code)
            else unquote_plus(course_code)
        )

        this_user = self.nbex_user

        if not course_code in this_user["courses"]:
            note = "User not subscribed to course {}".format(course_code)
            self.log.info(note)
            self.write({"success": False, "value": models, "note": note})

        # Find the course being referred to
        course = orm.Course.find_by_code(
            db=self.db, code=course_code, org_id=this_user["org_id"], log=self.log
        )
        if course is None:
            note = "Course {} does not exist".format(course_code)
            self.log.info(note)
            self.write({"success": False, "value": models, "note": note})

        self.log.debug("Course:{}".format(course_code))
        # we're passing in the course object here

        models = []

        assignments = orm.Assignment.find_for_course(db=self.db, course_id=course.id)
        for assignment in assignments:
            for action in assignment.actions:
                models.append(
                    {
                        "assignment_id": assignment.assignment_code,
                        "course_id": assignment.course.course_code,
                        "status": action.action,  # currently called 'action' in our db
                        "path": action.location,
                        "notebooks": [],  # TODO: Nbgrader expexts this for some reason (but doesn't use it anywhere)
                        "timestamp": datetime.datetime.now(gettz("UTC")).strftime(
                            "%Y-%m-%d %H:%M:%S.%f %Z"
                        ),  # TODO: this should be pulled from the database
                    }
                )

        self.log.debug("Assignments: {}".format(models))
        self.write({"success": True, "value": models})


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

    @web.authenticated
    def get(self):  # def get(self, course_code, assignment_code=None):
        self.log.debug("+++++ assignment GET starting")

        params = self.request.arguments
        self.log.debug("params:{}".format(params))
        course_code = (
            self.request.arguments["course_id"][0].decode("utf-8")
            if "course_id" in self.request.arguments
            else None
        )
        assignment_code = (
            self.request.arguments["assignment_id"][0].decode("utf-8")
            if "assignment_id" in self.request.arguments
            else None
        )

        models = []

        if not course_code and not assignment_code:
            self.log.info(
                "Assigment call requires both a course code and an assignment code!!"
            )
            return

        # Un url-encode variables
        course_code = (
            unquote(course_code)
            if re.search("%20", course_code)
            else unquote_plus(course_code)
        )

        assignment_code = (
            unquote(assignment_code)
            if re.search("%20", assignment_code)
            else unquote_plus(assignment_code)
        )

        this_user = self.nbex_user

        if not course_code in this_user["courses"]:
            note = f"User not subscribed to course {course_code}"
            self.log.info(note)
            self.write({"success": False, "note": note})

        # Find the course being referred to
        course = orm.Course.find_by_code(
            db=self.db, code=course_code, org_id=this_user["org_id"], log=self.log
        )
        if course is None:
            note = f"Course {course_code} does not exist"
            self.log.info(note)
            self.write({"success": False, "note": note})
            return  # needs a proper 'fail' here

        note = ""
        self.log.debug("Course:{} assignment:{}".format(course_code, assignment_code))

        # The location for the data-object is actually held in the 'released' action for the given assignment
        # We want the last one...
        assignment = orm.Assignment.find_by_code(
            db=self.db, code=assignment_code, course_id=course.id
        )
        self._headers = httputil.HTTPHeaders(
            {
                "Content-Type": "application/gzip",
                "Date": httputil.format_timestamp(time.time()),
            }
        )
        if assignment:
            self.log.info(
                "Adding action {} for user {} against assignment {}".format(
                    "download", this_user["ormUser"].id, assignment.id
                )
            )
            data = b""

            release_file = None
            for action in assignment.actions:
                self.log.info(f"Action: {action.action}")
                if action.action == "released":
                    self.log.info(f"Found release: {action.location}")
                    release_file = action.location
                    # no break, as we want the /last/ released action!

            try:
                handle = open(release_file, "r+b")
                data = handle.read()
                handle.close
            except Exception as e:  # TODO: exception handling
                self.log.warning(f"Error: {e}")  # TODO: improve error message
                self.log.info("Recovery failed")

                # error 500??
                raise Exception

            action = orm.Action(
                user_id=this_user["ormUser"].id,
                assignment_id=assignment.id,
                action="fetched",
<<<<<<< HEAD
                location=release_file,
=======
                location="/tmp/nbgrader-expects-a-file-path",  # TODO: nbgrader expets a file path here.
>>>>>>> 4710a80839f78740e40dd55eacc381da9aae55ac
            )
            self.db.add(action)
            self.db.commit()
            self.log.info("action commited")
            self.write(data)
        else:
            self.write(data)

    # This is releasing an **assignment**, not a student submission
    @web.authenticated
    def post(self):

        course_code = self.request.arguments["course_id"][0].decode("utf-8")
        assignment_code = (
            self.request.arguments["assignment_id"][0].decode("utf-8")
            if "assignment_id" in self.request.arguments
            else None
        )

        self.log.debug(
            f"Called POST /assignment with arguments: course {course_code} and  assignment {assignment_code}"
        )
        if not (course_code and assignment_code):
            note = "Posting an Assigment requires a course code and an assignment code"
            self.log.info(note)
            self.write({"success": False, "note": note})

        # Un url-encode variables
        course_code = (
            unquote(course_code)
            if re.search("%20", course_code)
            else unquote_plus(course_code)
        )
        assignment_code = (
            unquote(assignment_code)
            if re.search("%20", assignment_code)
            else unquote_plus(assignment_code)
        )

        this_user = self.nbex_user
        if not course_code in this_user["courses"]:
            note = "User not subscribed to course {}".format(course_code)
            self.log.info(note)
            self.write({"success": False, "note": note})
        if not "instructor" in this_user["courses"][course_code]:
            note = "User not an instructor to course {}".format(course_code)
            self.log.info(note)
            self.write({"success": False, "note": note})

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
            self.log.info(
                "New Assignment details: assignment_code:{}, course_id:{}".format(
                    assignment_code, course.id
                )
            )
            # defaults active
            assignment = orm.Assignment(
                assignment_code=assignment_code, course_id=course.id
            )
            self.db.add(assignment)
            # deliberately no commit: we need to be able to roll-back if there's no data!

        # storage is dynamically in $path/release/$course_code/$assignment_code/<timestamp>/
        # Note - this means we can have multiple versions of the same release on the system
        release_file = "/".join(
            [
                self.base_storage_location,
                "released",
                course_code,
                assignment_code,
                str(int(time.time())),
            ]
        )

        model = []

        try:
            # Write the uploaded file to the desired location
            file_info = self.request.files["assignment"][0]

            filename, content_type = file_info["filename"], file_info["content_type"]
            note = "Received file {}, of type {}".format(filename, content_type)
            self.log.info(note)
            model.append(note)
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

            self.log.info("Upload failed")
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
            "!!!!!!!!!!!!!! assignment details for upload:{}|{}".format(
                assignment.id, assignment.course_id
            )
        )
        action = orm.Action(
            user_id=this_user["ormUser"].id,
            assignment_id=assignment.id,
            action="released",
            location=release_file,
        )
        self.db.add(action)
        self.db.commit()
        self.write({"success": True, "note": "Released"})


default_handlers = [Assignment, Assignments]
