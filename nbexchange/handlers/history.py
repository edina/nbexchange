# import os
# import time
# import uuid

from sqlalchemy import desc
from tornado import web, httputil

import nbexchange.models.assignments
import nbexchange.models.courses
import nbexchange.models.notebooks
import nbexchange.models.subscriptions
from nbexchange.database import scoped_session
from nbexchange.handlers.base import BaseHandler, authenticated

"""
All URLs relative to /services/nbexchange

This relys on users being logged in, and the user-object having additional data:
'role' (as per LTI)
"""


class History(BaseHandler):
    """.../actions/

    GET: gets list of actions relevent to the user.

    Returns a list of data:

    [
        {
            course_id: Int,
            course_code: Str,
            course_title: Str,
            roles: [Str, Str, ..],
            was_instructor: Bool,
            assignments: [
                {
                    assignment_code: Str,
                    active: Bool,
                    actions: [
                        action: 
                    ]
                },
            ],
       },
       {...},
    ]

data = {}
uid = 13
with scoped_session() as session:
    rows = session.query(nbexchange.models.Subscription).filter_by(user_id=uid).all()
    for row in rows:
        pk = row.course.id
        if pk not in data:
            data[pk] = dict()
            data[pk]['role'] = dict()
            data[pk]['user_id'] = dict()
            data[pk]['assignments'] = list()
            data[pk]['isInstructor'] = False
        data[pk]['course_id'] = pk
        data[pk]['course_code'] = row.course.course_code
        data[pk]['course_title'] = row.course.course_title
        data[pk]['role'][row.role] = 1
        data[pk]['user_id'][row.user_id] = 1
        if row.role == 'Instructor':
            data[pk]['isInstructor'] = True
        for assignment in row.course.assignments:
            if assignment.active:
                a = dict()
                a['assignment_id'] = assignment.id
                a['assignment_code'] = assignment.assignment_code
                a['actions'] = list()
                for action in assignment.actions:
                    if action.action == 'released' or action.user_id == uid or row.role == 'Instructor':
                        b = dict()
                        b['action'] = str(action.action)
                        b['timestamp'] = action.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f %Z")
                        user = nbexchange.models.users.User.find_by_pk(db=session, pk=action.user_id)
                        b['user'] = user.name
                        a['actions'].append(b)
                data[pk]['assignments'].append(a)

    """

    urls = ["history"]

    @authenticated
    def get(self):

        models = []

        # Who is my user?
        this_user = self.nbex_user
        self.log.debug(f"User: {this_user.get('name')}")

        # Find all the assignments this user should be able to see
        with scoped_session() as session:
            rows = session.query(nbexchange.models.Subscription).filter_by(user_id=this_user["id"]).all()
            for row in rows:
                data = dict()
                data['role'] = dict()
                data['user_id'] = dict()
                data['assignments'] = list()
                data['isInstructor'] = False

                data['course_id'] = row.course.id
                data['course_code'] = row.course.course_code
                data['course_title'] = row.course.course_title
                data['role'][row.role] = 1
                data['user_id'][row.user_id] = 1
                if row.role == 'Instructor':
                    data['isInstructor'] = True
                for assignment in row.course.assignments:
                    if assignment.active:
                        a = dict()
                        a['assignment_id'] = assignment.id
                        a['assignment_code'] = assignment.assignment_code
                        a['actions'] = list()
                        for action in assignment.actions:
                            if action.action == 'released' or action.user_id == this_user["id"] or row.role == 'Instructor':
                                b = dict()
                                b['action'] = str(action.action)
                                b['timestamp'] = action.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f %Z")
                                user = nbexchange.models.users.User.find_by_pk(db=session, pk=action.user_id)
                                b['user'] = user.name
                                a['actions'].append(b)
                        data['assignments'].append(a)
                    models.append(data)

        self.log.debug(f"History: {models}")
        self.finish({"success": True, "value": models})

    # This has no authentiction wrapper, so false implication os service
    def post(self):
        raise web.HTTPError(501)
