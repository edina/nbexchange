import functools
import re
from datetime import datetime
from typing import Awaitable, Callable, Optional
from urllib.parse import unquote, unquote_plus
from zoneinfo import ZoneInfo

from tornado import web
from tornado.log import app_log

from nbexchange.database import scoped_session
from nbexchange.models.courses import Course
from nbexchange.models.subscriptions import Subscription
from nbexchange.models.users import User

SPACE_ENCODED_PATTERN = re.compile(r"%20")


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

    urls = []

    def __init__(self, application, request, **kwargs):
        super(BaseHandler, self).__init__(application, request, **kwargs)
        self.set_header("Content-type", "application/json")
        self._nbex_user_cache = None

    @property
    def timezone(self):
        return self.settings["timezone"]

    @property
    def timestamp_format(self):
        return self.settings["timestamp_format"]

    def check_timezone(self, value: datetime) -> datetime:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            value = value.replace(tzinfo=ZoneInfo(self.timezone))
        return value

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

    def _get_or_create_user(self, session, hub_username, org_id, full_name, email, lms_user_id):
        """Get or create a user record.

        Returns:
            User object
        """
        user = User.find_by_name(db=session, name=hub_username, log=self.log)
        if user is None:
            self.log.debug(f"New user details: name:{hub_username}, org_id:{org_id}")
            user = User(name=hub_username, org_id=org_id, full_name=full_name, email=email, lms_user_id=lms_user_id)
            session.add(user)
            session.flush()
        elif user.full_name != full_name:
            user.full_name = full_name

        return user

    def _get_or_create_course(self, session, course_code, org_id, course_title):
        """Get or create a course record.

        Returns:
            Course object
        """
        course = Course.find_by_code(db=session, code=course_code, org_id=org_id, log=self.log)
        if course is None:
            self.log.debug(f"New course details: code:{course_code}, org_id:{org_id}")
            course = Course(org_id=org_id, course_code=course_code)
            if course_title:
                self.log.debug(f"Adding title {course_title}")
                course.course_title = course_title
            session.add(course)
            session.flush()

        return course

    def _get_or_create_subscription(self, session, user_id, course_id, role):
        """Get or create a subscription record.

        Returns:
            Subscription object
        """
        subscription = Subscription.find_by_set(db=session, user_id=user_id, course_id=course_id, role=role)
        if subscription is None:
            self.log.debug(f"New subscription details: user:{user_id}, course:{course_id}, role:{role}")
            subscription = Subscription(user_id=user_id, course_id=course_id, role=role)
            session.add(subscription)
            session.flush()

        return subscription

    def _build_courses_dict(self, user):
        """Build the courses dictionary from user subscriptions.

        Returns:
            dict: {course_code: {role: 1}}
        """
        courses = {}
        for subscription in user.courses:
            if subscription.course.course_code not in courses:
                courses[subscription.course.course_code] = {}
            courses[subscription.course.course_code][subscription.role] = 1
        return courses

    @property
    def nbex_user(self):
        """Get or create the current user's nbexchange record.

        This property is cached per request to avoid repeated database queries.
        Creates/updates user, course, and subscription records as needed.

        Returns:
            dict: User model with course subscriptions

        Raises:
            ValueError: If course_id or course_role are missing from user data
        """
        if self._nbex_user_cache is not None:
            return self._nbex_user_cache

        hub_user = self.get_current_user()
        hub_username = hub_user.get("name")
        full_name = hub_user.get("full_name")
        current_course = hub_user.get("course_id")
        current_role = hub_user.get("course_role")
        course_title = hub_user.get("course_title", "no_title")
        org_id = hub_user.get("org_id", 1)
        email = hub_user.get("email")
        lms_user_id = hub_user.get("lms_user_id")

        if not (current_course and current_role):
            note = (
                f"Both current_course ('{current_course}') and current_role ('{current_role}')"
                + f" must have values. User was '{hub_username}'"  # noqa: W503
            )
            self.log.info(note)
            raise ValueError(note)

        self.org_id = org_id

        with scoped_session() as session:
            user = self._get_or_create_user(session, hub_username, org_id, full_name, email, lms_user_id)

            course = self._get_or_create_course(session, current_course, org_id, course_title)

            # create if it doesn't exist.
            self._get_or_create_subscription(session, user.id, course.id, current_role)

            courses = self._build_courses_dict(user)

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

        self._nbex_user_cache = model
        return model

    @property
    def log(self):
        """I can't seem to avoid typing self.log"""
        return self.settings.get("log", app_log)

    def param_decode(self, value):
        """Decode URL-encoded parameter values."""
        if value is None:
            return None
        if SPACE_ENCODED_PATTERN.search(value):
            return unquote(value)
        return unquote_plus(value)

    def get_params(self, param_list):
        """Extract and decode multiple parameters from request."""
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
