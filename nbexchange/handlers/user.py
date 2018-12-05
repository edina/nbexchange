from nbexchange.base import BaseHandler
from tornado import web

"""
All URLs relative to /services/nbexchange

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
