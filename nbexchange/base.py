import re
import requests
import functools

import nbexchange.models.courses
import nbexchange.models.subscriptions
import nbexchange.models.users
from tornado import web
from tornado.log import app_log
from raven.contrib.tornado import SentryMixin
from urllib.parse import unquote, unquote_plus
from nbexchange.database import scoped_session

from typing import Optional, Awaitable, Callable


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


class BaseHandler(SentryMixin, web.RequestHandler):
    """An nbexchange base handler"""

    # register URL patterns
    urls = []

    # Root location for data to be written to
    @property
    def base_storage_location(self):
        return self.settings["base_storage_location"]

    @property
    def naas_url(self):
        return self.settings["naas_url"]

    def get_current_user(self):

        # Call Django to Authenticate Our User
        api_endpoint = f"{self.naas_url}/api/users/current/"

        cookies = dict()
        # Pass through cookies
        for name in self.request.cookies:
            cookies[name] = self.get_cookie(name)

        try:
            r = requests.get(api_endpoint, cookies=cookies)
        except requests.exceptions.ConnectionError:
            return None

        result = r.json()

        self.log.debug("CODE: {} \nRESULT: {}".format(r.status_code, result))

        if r.status_code == 401:
            return None

        return {
            "name": result["username"],
            "course_id": result["course_code"],
            "course_title": result["course_title"],
            "course_role": result["role"],
        }

    @property
    def nbex_user(self):

        hub_user = self.get_current_user()
        hub_username = hub_user.get("name")

        current_course = hub_user.get("course_id")
        current_role = hub_user.get("course_role")
        course_title = hub_user.get("course_title", "no_title")

        if not (current_course and current_role):
            return

        # TODO: this puts a hard restriction on the usernames having an underscore in them, which we do not want
        # THe solution is to get the organisation id from the user state stored in jupyterhub instead of deriving it
        # from the username
        try:
            org_id, name = hub_user.get("name").split(
                "_", 1
            )  # we only want the first part
        except ValueError:
            org_id = 1

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
