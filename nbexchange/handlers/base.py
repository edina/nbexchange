import functools
import re
from typing import Optional, Awaitable, Callable
from urllib.parse import unquote, unquote_plus

import requests
from tornado import web
from tornado.log import app_log

import nbexchange.models.courses
import nbexchange.models.subscriptions
import nbexchange.models.users
from nbexchange.database import scoped_session


def authenticated(
    method: Callable[..., Optional[Awaitable[None]]]
) -> Callable[..., Optional[Awaitable[None]]]:
    """Decorate methods with this to require that the user be logged in.

    If the user is not logged in, raise a 403 error
    """

    @functools.wraps(method)
    def wrapper(  # type: ignore
        self: web.RequestHandler, *args, **kwargs
    ) -> Optional[Awaitable[None]]:
        if not self.current_user:
            raise web.HTTPError(403)
        return method(self, *args, **kwargs)

    return wrapper


class BaseHandler(web.RequestHandler):
    """An nbexchange base handler"""

    # register URL patterns
    urls = []

    def __init__(self, application, request, **kwargs):
        super(BaseHandler, self).__init__(application, request, **kwargs)
        self.set_header("Content-type", "application/json")

    # Root location for data to be written to
    @property
    def base_storage_location(self):
        return self.settings["base_storage_location"]

    @property
    def user_plugin(self):
        return self.settings["user_plugin"]

    def get_current_user(self):
        return self.user_plugin.get_current_user(self)

    @property
    def nbex_user(self):

        hub_user = self.get_current_user()
        hub_username = hub_user.get("name")

        current_course = hub_user.get("course_id")
        current_role = hub_user.get("course_role")
        course_title = hub_user.get("course_title", "no_title")
        org_id = hub_user.get("org_id", 1)

        if not (current_course and current_role):
            return

        self.org_id = org_id

        with scoped_session() as session:
            user = nbexchange.models.users.User.find_by_name(
                db=session, name=hub_username, log=self.log
            )
            if user is None:
                self.log.debug(
                    f"New user details: name:{hub_username}, org_id:{org_id}"
                )
                user = nbexchange.models.users.User(name=hub_username, org_id=org_id)
                session.add(user)

            course = nbexchange.models.courses.Course.find_by_code(
                db=session, code=current_course, org_id=org_id, log=self.log
            )
            if course is None:
                self.log.debug(
                    f"New course details: code:{current_course}, org_id:{org_id}"
                )
                course = nbexchange.models.courses.Course(
                    org_id=org_id, course_code=current_course
                )
                if course_title:
                    self.log.debug(f"Adding title {course_title}")
                    course.course_title = course_title
                session.add(course)

            # Check to see if we have a subscription (for this course)
            self.log.debug(
                f"Looking for subscription for: user:{user.id}, course:{course.id}, role:{current_role}"
            )

            subscription = nbexchange.models.subscriptions.Subscription.find_by_set(
                db=session, user_id=user.id, course_id=course.id, role=current_role
            )
            if subscription is None:
                self.log.debug(
                    f"New subscription details: user:{user.id}, course:{course.id}, role:{current_role}"
                )
                subscription = nbexchange.models.subscriptions.Subscription(
                    user_id=user.id, course_id=course.id, role=current_role
                )
                session.add(subscription)

            courses = {}

            for subscription in user.courses:
                if not subscription.course.course_code in courses:
                    courses[subscription.course.course_code] = {}
                courses[subscription.course.course_code][subscription.role] = 1

            model = {
                "kind": "user",
                "id": user.id,
                "name": user.name,
                "org_id": user.org_id,
                "current_course": current_course,
                "current_role": current_role,
                "courses": courses,
            }
        return model

    @property
    def log(self):
        """I can't seem to avoid typing self.log"""
        return self.settings.get("log", app_log)

    def param_decode(self, value):
        unquote(value) if re.search("%20", value) else unquote_plus(value)
        return value

    def get_params(self, param_list):

        return_params = []

        for param in param_list:
            value = (
                self.request.arguments[param][0].decode("utf-8")
                if param in self.request.arguments
                else None
            )
            value = self.param_decode(value) if value else None
            return_params.append(value)
        return return_params


class Template404(BaseHandler):
    """Render nbexchange's 404 template"""

    urls = [".*"]

    def prepare(self):
        raise web.HTTPError(404)
