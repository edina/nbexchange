from tornado import web

from nbexchange.database import scoped_session
from nbexchange.handlers.base import BaseHandler, authenticated
from nbexchange.models.actions import Action, AssignmentActions
from nbexchange.models.assignments import Assignment as AssignmentModel
from nbexchange.models.courses import Course
from nbexchange.models.users import User

"""
All URLs relative to /services/nbexchange

This relys on users being logged in, and the user-object having additional data:
'role' (as per LTI)
"""


class Collections(BaseHandler):
    """.../collections/
    parmas:
        course_id: course_code
        assignment_id: assignment_code
        user_id: user_id - optional

    GET: gets list of actions for the assignment

    returns: list of notebooks available for collection

    {'success': True,
     'value': [
           {'assignment_id': <assignment_code>,
            'course_id': <course_code?,
            'full_name': user_id.full_name,
            'email': user_id.email,
            'lms_user_id': user_id.lms_user_id,
            'notebooks': [{'notebook_id': 'test'}],
            'path': </full/path/to/gzip/file/on/exchange/server.gz>,
            'status': <status.code>,
            'student_id': <user_id.name>,
            'timestamp': <timestamp of action>.strftime("%Y-%m-%d %H:%M:%S.%f %Z")
           },
           {....}, ....
        ]
    }
    """

    urls = ["collections"]

    @authenticated
    def get(self):
        models = []

        [course_code, assignment_code, user_id] = self.get_params(["course_id", "assignment_id", "user_id"])

        if not (course_code and assignment_code):
            note = "Collections call requires both a course code and an assignment code"
            self.log.info(note)
            self.finish({"success": False, "note": note})
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
            self.finish({"success": False, "note": note})
            return
        if not "instructor" == this_user["current_role"].casefold():  # we may need to revisit this
            note = f"User not an instructor to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        # Find the course being referred to
        with scoped_session() as session:
            course = Course.find_by_code(db=session, code=course_code, org_id=this_user["org_id"], log=self.log)
            if not course:
                note = f"Course {course_code} does not exist"
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return

            assignment = AssignmentModel.find_by_code(
                db=session,
                course_id=course.id,
                log=self.log,
                code=assignment_code,
                action=AssignmentActions.submitted.value,
            )

            if not assignment:
                note = f"Assignment {assignment_code} does not exist"
                self.log.info(note)
                self.finish({"success": True, "value": []})
                return

            self.log.debug(f"Assignment: {assignment}")

            filters = [
                Action.assignment_id == assignment.id,
                Action.action == AssignmentActions.submitted.value,
            ]

            if user_id:
                student = session.query(User).filter(User.name == user_id).first()
                filters.append(Action.user_id == student.id)

            actions = session.query(Action).filter(*filters)

            for action in actions:
                models.append(
                    {
                        "student_id": action.user.name,
                        "full_name": action.user.full_name,
                        "email": action.user.email,
                        "lms_user_id": action.user.lms_user_id,
                        "assignment_id": assignment.assignment_code,
                        "course_id": assignment.course.course_code,
                        "status": action.action.value,  # currently called 'action' in our db
                        "path": action.location,
                        # 'name' in db, 'notebook_id' id nbgrader
                        "notebooks": [{"notebook_id": x.name} for x in assignment.notebooks],
                        "timestamp": action.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f %Z"),
                    }
                )

            self.log.debug(f"Assignments: {models}")
        self.finish({"success": True, "value": models})

    # This has no authentiction wrapper, so false implication os service
    def post(self):
        raise web.HTTPError(501)


class Collection(BaseHandler):
    """.../collection/
    parmas:
        course_id: course_code
        assignment_id: assignment_code
        path: url_encoded_path

    GET: Downloads the specified file (checking that it's "submitted", for this course/assignment,
    and the user has access to do so)
    """

    urls = ["collection"]

    @authenticated
    def get(self):
        [course_code, assignment_code, path] = self.get_params(["course_id", "assignment_id", "path"])

        if not (course_code and assignment_code and path):
            note = "Collection call requires a course code, an assignment code, and a path"
            self.log.info(note)
            self.finish({"success": False, "note": note})
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
            self.finish({"success": False, "note": note})
            return
        self.log.info(f"user: {this_user}")

        if not "instructor" == this_user["current_role"].casefold():  # we may need to revisit this
            note = f"User not an instructor to course {course_code}"
            self.log.info(note)
            self.finish({"success": False, "note": note})
            return

        # Find the course being referred to
        with scoped_session() as session:
            course = Course.find_by_code(db=session, code=course_code, org_id=this_user["org_id"], log=self.log)
            if not course:
                note = f"Course {course_code} does not exist"
                self.log.info(note)
                self.finish({"success": False, "note": note})
                return

            # We need to key off the assignment, but we're actually looking
            # for the action with a action and a specific path
            assignments = AssignmentModel.find_for_course(
                db=session,
                course_id=course.id,
                log=self.log,
                action=AssignmentActions.submitted.value,
                path=path,
            )

            self.set_header("Content-Type", "application/gzip")

            # I do not want to assume there will just be one.
            for assignment in assignments:
                self.log.debug(f"Assignment: {assignment}")

                try:
                    with open(path, "r+b") as handle:
                        data = handle.read()
                except Exception as e:  # TODO: exception handling
                    self.log.warning(f"Error: {e}")  # TODO: improve error message

                    # error 500??
                    raise Exception

                self.log.info(
                    f"Adding action {AssignmentActions.collected.value} for user {this_user['id']} against assignment {assignment.id}"  # noqa: E501
                )
                action = Action(
                    user_id=this_user["id"],
                    assignment_id=assignment.id,
                    action=AssignmentActions.collected,
                    location=path,
                )
                session.add(action)

                self.finish(data)
                return

    # This has no authentiction wrapper, so false implication os service
    def post(self):
        raise web.HTTPError(501)
