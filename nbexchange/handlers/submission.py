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

Submission calls:
.../submissions/$course_code/$assignment_code/
GET: gets list of users who've submitted so far
.../submissions/$course_code/$assignment_code/$username
GET: gets list is submissions for that user (may be more than 1!)

.../submission/$course_code/$assignment_code/$username
GET: gets the assignment for that user [Instructor only]
POST (with data) stores the submission for that user

This relys on users being logged in, and the user-object having additional data:
'role' (as per LTI)
"""


class Submission(BaseHandler):
    urls = ["submission"]

    pass


class Submissions(BaseHandler):
    urls = ["submissions"]

    @web.authenticated
    def post(self):

        self.write("##### I received a POST for /submissions")


default_handlers = [Submission, Submissions]
