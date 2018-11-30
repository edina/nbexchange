import datetime
import json
import os
import random
import re
import uuid

from dateutil.tz import gettz

from nbexchange import orm
from nbexchange.base import BaseHandler

from tornado import web
from urllib.parse import quote_plus, unquote, unquote_plus
from urllib.request import urlopen

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


default_handlers = [EnvHandler, HomeHandler, User, Feedback]
