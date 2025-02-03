import functools
import re
from datetime import datetime
from typing import Awaitable, Callable, Optional
from urllib.parse import unquote, unquote_plus
from zoneinfo import ZoneInfo

from dateutil.tz import gettz
from tornado import web
from tornado.log import app_log

from nbexchange.database import scoped_session
from nbexchange.models.courses import Course
from nbexchange.models.subscriptions import Subscription
from nbexchange.models.users import User


def authenticated(method: Callable[..., Optional[Awaitable[None]]]) -> Callable[..., Optional[Awaitable[None]]]:
    """Decorate methods with this to require that the user be logged in.

    If the user is not logged in, raise a 403 error
    """

    @functools.wraps(method)
    def wrapper(self: web.RequestHandler, *args, **kwargs) -> Optional[Awaitable[None]]:  # type: ignore
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

    # hard-coded copy of nbgrader.exchange.timezone
    timezone = "UTC"
    # @property
    # def timezone(self):
    #     return self.settings["timezone"]

    # hard-coded copy of nbgrader.exchange.timestamp_format
    timestamp_format = "%Y-%m-%d %H:%M:%S.%f %Z"
    # @property
    # def timestamp_format(self):
    #     return self.settings['timestamp_format']

    def get_timestamp(self) -> datetime:
        tz = gettz(self.timezone)
        timestamp = datetime.now(tz).strftime(self.timestamp_format)
        return timestamp

    def check_timezone(self, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            value = value.replace(tzinfo=ZoneInfo(self.timezone))
        return value

    # Root location for data to be written to
    @property
    def base_storage_location(self):
        return self.settings["base_storage_location"]

    @property
    def user_plugin(self):
        return self.settings["user_plugin"]

    @property
    def max_buffer_size(self):
        return self.settings["max_buffer_size"]

    def get_current_user(self):
        return self.user_plugin.get_current_user(self)

    @property
    def nbex_user(self):
        hub_user = self.get_current_user()
        hub_username = hub_user.get("name")

        full_name = hub_user.get("full_name")
        current_course = hub_user.get("course_id")
        current_role = hub_user.get("course_role")
        course_title = hub_user.get("course_title", "no_title")
        org_id = hub_user.get("org_id", 1)
        email = hub_user.get("email")
        lms_user_id = hub_user.get("lms_user_id")

        # Raising an error appears to have no detrimental affect when running.
        if not (current_course and current_role):
            note = f"Both current_course ('{current_course}') and current_role ('{current_role}') must have values. User was '{hub_username}'"  # noqa: E501
            self.log.info(note)
            raise ValueError(note)

        self.org_id = org_id

        with scoped_session() as session:
            user = User.find_by_name(db=session, name=hub_username, log=self.log)
            if user is None:
                self.log.debug(f"New user details: name:{hub_username}, org_id:{org_id}")
                user = User(name=hub_username, org_id=org_id, email=email, lms_user_id=lms_user_id)
                session.add(user)
            if user.full_name != full_name:
                user.full_name = full_name

            course = Course.find_by_code(db=session, code=current_course, org_id=org_id, log=self.log)
            if course is None:
                self.log.debug(f"New course details: code:{current_course}, org_id:{org_id}")
                course = Course(org_id=org_id, course_code=current_course)
                if course_title:
                    self.log.debug(f"Adding title {course_title}")
                    course.course_title = course_title
                session.add(course)

            # Check to see if we have a subscription (for this course)
            self.log.debug(f"Looking for subscription for: user:{user.id}, course:{course.id}, role:{current_role}")

            subscription = Subscription.find_by_set(db=session, user_id=user.id, course_id=course.id, role=current_role)
            if subscription is None:
                self.log.debug(f"New subscription details: user:{user.id}, course:{course.id}, role:{current_role}")
                subscription = Subscription(user_id=user.id, course_id=course.id, role=current_role)
                session.add(subscription)

            courses = {}

            for subscription in user.courses:
                if subscription.course.course_code not in courses:
                    courses[subscription.course.course_code] = {}
                courses[subscription.course.course_code][subscription.role] = 1

            model = {
                "kind": "user",
                "id": user.id,
                "name": user.name,
                "email": email,
                "lms_user_id": lms_user_id,
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
            value = self.request.arguments[param][0].decode("utf-8") if param in self.request.arguments else None
            value = self.param_decode(value) if value else None
            return_params.append(value)
        return return_params


class Template404(BaseHandler):
    """Render nbexchange's 404 template"""

    urls = [".*"]

    def prepare(self):
        raise web.HTTPError(404)
