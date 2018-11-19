import json
import os
import re

from nbexchange import orm
from nbexchange.base import BaseHandler

from tornado import web
from urllib.parse import quote_plus, unquote, unquote_plus
from urllib.request import urlopen

"""
All URLs relative to /services/nbexchange



Assignment calls:
.../assignment/$course_code/$assignment_code
GET: Downloads that assignment
POST maybe

Submission calls:
.../submissions/$course_code/$assignment_code/
GET: gets list of users who've submitted so far
.../submissions/$course_code/$assignment_code/$username
GET: gets list is submissions for that user (may be more than 1!)

.../submission/$course_code/$assignment_code/$username
GET: gets the assignment for that user [Instructor only]
POST (with data) stores the submission for that user

.../feedback/$course_code/$assignment_code/$username
GET: gets the feedback [instructors can see any relevant student, other their own only]
POST: uploads feedback [instructors only]

This relys on users being logged in, and the user-object having additional data:
'role' (as per LTI)
"""


class User(BaseHandler):
    """
    .../user
GET: gets the user (creates if not present), and subscribes to the current course with the current role.
    """

    # url responds to '/usr', '/usr/', '/usr/$role', '/usr/$role/',...
    urls = ["/user/?"]

    @web.authenticated
    def get(self, role=None, course_code=None, course_title=None):

        # user is a dict
        user = self.nbex_user

        self.finish(self.render_template("user.html", nbex_user=user))


class Assignment(BaseHandler):
    """.../assignment/$course_code[/$assignment_code]
GET: (without assignment_code) gets list of assignments for $course_code
     (with assignment_code) downloads assignment
POST: (with assignment_code, role=instructor, with data): Add ("release") an assignment
"""

    urls = ["assignment/([^/]+)(?:/?([^/]+))?"]

    @web.authenticated
    def get(self, course_code, assignment_code=None):

        assignment = None
        models = []

        if not course_code:
            self.log.info("Assigment call requires a course code!!")
            return

        # Un url-encode variables
        course_code = (
            unquote(course_code)
            if re.search("%20", course_code)
            else unquote_plus(course_code)
        )
        if assignment_code:
            assignment_code = (
                unquote(assignment_code)
                if re.search("%20", assignment_code)
                else unquote_plus(assignment_code)
            )

        this_user = self.nbex_user

        if not course_code in this_user["courses"]:
            self.log.info("User not subscribed to course {}".format(course_code))
            return

        # Find the course being referred to
        course = orm.Course.find_by_code(
            db=self.db, code=course_code, org_id=this_user["org_id"], log=self.log
        )
        if course is None:
            self.log.info("Course {} does not exist".format(course_code))
            return

        if assignment_code:
            assignment = orm.Assignment.find_by_code(
                db=self.db, code=assignment_code, course_id=course.id
            )
            if assignment:
                models.append(
                    {
                        "ormAssignment": assignment,
                        "assignment_code": assignment_code,
                        "course": assignment.course.course_code,
                        "actions": [
                            [action.user.name, action.action.role]
                            for action in assignment.actions
                        ],
                    }
                )
                action = orm.Action(
                    user_id=this_user["ormUser"].id,
                    assignment_id=assignment.id,
                    action="download",
                )
                self.db.add(action)
                self.db.commit()
            else:
                self.log.info("No assignments for course {}".format(course_code))

        else:
            ## return list of assignments for this course
            assignments = orm.Assignment.find_for_course(
                db=self.db, course_id=course.id
            )
            for assignment in assignments:
                models.append(
                    {
                        "ormAssignment": assignment,
                        "assignment_code": assignment_code,
                        "course": assignment.course.course_code,
                        "actions": [
                            [action.user.name, action.action.role]
                            for action in assignment.actions
                        ],
                    }
                )

        self.log.info("Assignments: {}".format(models))
        self.write(models)


    # This is uploading an **assignment**, not a submission
    @web.authenticated
    def post(self, course_code, assignment_code=None):

        if not (course_code and assignment_code):
            self.log.info(
                "Posting an Assigment requires a course code and an assignment code"
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
            self.log.info("User not subscribed to course {}".format(course_code))
            return
        if not "instructor" in this_user["courses"][course_code]:
            self.log.info("User not an instructor to course {}".format(course_code))
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

        # storage is dynamically in $path/release/$course_code/$assignment_code/$index/
        # $index is currently hard-coded to '1' (meaning we over-write re-submissions)
        index = 1
        path = "/".join(
            self.base_storage_location, "release", course_code, assignment_code, index
        )

        model = []

        try:
            ## from https://github.com/tornadoweb/tornado/blob/master/demos/file_upload/file_receiver.py
            for field_name, files in self.request.files.items():
                for info in files:
                    filename, content_type = info["filename"], info["content_type"]
                    body = info["body"]
                    note = "Recieved file {}, of type {}".format(filename, content_type)
                    self.log.info(note)
                    model.append(note)

                    # store to disk.
                    # This should be abstracted, so it can be overloaded to store in other manners (eg AWS)
                    release_filename = path + "/" + filename
                    handle = os.open(release_filename, "wb")
                    handle.write(body)

        except:
            self.log.info("Upload failed")
            self.db.rollback()
            # error 500??
            return

        # Record the action.
        # Note we record the path to the files.
        action = orm.Action(
            user_id=this_user["ormUser"].id,
            assignment_id=assignment.id,
            action="release",
            location=path,
        )
        self.db.add(action)
        self.db.commit()

        self.finish(
            self.render_template(
                "release.html", nbex_user=this_user, nbex_release=model
            )
        )


class Submission(BaseHandler):
    urls = ["submission"]
    pass


class Submissions(BaseHandler):
    urls = ["submissions"]
    pass


class Feedback(BaseHandler):
    urls = ["/feedback"]
    pass


class EnvHandler(BaseHandler):
    urls = ["/env"]

    def get(self):
        self.finish(self.render_template("env.html", env=os.environ))


class HomeHandler(BaseHandler):
    urls = ["/"]

    def get(self):
        self.log.info("################  Hello World, this is home")
        self.write("################  Hello World, this is home")


default_handlers = [
    EnvHandler,
    HomeHandler,
    User,
    Assignment,
    Submission,
    Submissions,
    Feedback,
]
