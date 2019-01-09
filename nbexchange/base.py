import re
import os
import requests
from jupyterhub.handlers import BaseHandler as JupyterHubBaseHandler
from jupyterhub.services.auth import HubAuthenticated, HubOAuthenticated
from jupyterhub.utils import url_path_join
from nbexchange import orm
from tornado import gen, web
from raven.contrib.tornado import SentryMixin
from urllib.parse import quote_plus, unquote, unquote_plus


class BaseHandler(HubOAuthenticated, SentryMixin, JupyterHubBaseHandler):
    """An nbexchange base handler"""

    # register URL patterns
    urls = []

    # Root location for data to be written to
    base_storage_location = "/disk/remote/courses"  # TODO should be a config parameter

    def get_auth_state(self, username=None):
        url = f"{self.settings['hub_api_url']}users/{username}"
        headers = {"Authorization": f"token {os.environ.get('JUPYTERHUB_API_TOKEN')}"}
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        user = r.json()
        return user.get("auth_state", {})

    @property
    def nbex_user(self):

        hub_user = self.get_current_user()
        hub_username = hub_user.get("name")
        hub_auth_state = self.get_auth_state(username=hub_username)

        ### Bodge.

        current_course = hub_auth_state.get("course_id")
        current_role = hub_auth_state.get("course_role")
        course_title = hub_auth_state.get("course_title", "no_title")

        if not (current_course and current_role):
            return

        # TODO: this puts a hard restriction on the usernames having an underscore in them, which we do not want
        # THe solution is to get the organisation id from the user state stored in jupyterhub instead of deriving it
        # from the username
        org_id, name = hub_user.get("name").split("_", 1)  # we only want the first part
        org_id = 1 if org_id is None else org_id
        self.org_id = org_id

        user = orm.User.find_by_name(db=self.db, name=hub_username, log=self.log)
        if user is None:
            self.log.debug(f"New user details: name:{hub_username}, org_id:{org_id}")
            user = orm.User(name=hub_username, org_id=org_id)
            self.db.add(user)

        course = orm.Course.find_by_code(
            db=self.db, code=current_course, org_id=org_id, log=self.log
        )
        if course is None:
            self.log.debug(
                f"New course details: code:{current_course}, org_id:{org_id}"
            )
            course = orm.Course(org_id=org_id, course_code=current_course)
            if course_title:
                self.log.debug(f"Adding title {course_title}")
                course.course_title = course_title
            self.db.add(course)

        # Check to see if we have a subscription (for this course)
        self.log.debug(
            f"Looking for subscription for: user:{user.id}, course:{course.id}, role:{current_role}"
        )

        subscription = orm.Subscription.find_by_set(
            db=self.db, user_id=user.id, course_id=course.id, role=current_role
        )
        if subscription is None:
            self.log.debug(
                f"New subscription details: user:{user.id}, course:{course.id}, role:{current_role}"
            )
            subscription = orm.Subscription(
                user_id=user.id, course_id=course.id, role=current_role
            )
            self.db.add(subscription)

        self.db.commit()

        courses = {}

        for subscription in user.courses:
            if not subscription.course.course_code in courses:
                courses[subscription.course.course_code] = {}
            courses[subscription.course.course_code][subscription.role] = 1

        model = {
            "kind": "user",
            "ormUser": user,
            "name": user.name,
            "org_id": user.org_id,
            "current_course": current_course,
            "current_role": current_role,
            "courses": courses,
            "auth_state": hub_auth_state,
        }
        return model

    @property
    def hub_auth(self):
        return self.settings.get("hub_auth")

    @property
    def csp_report_uri(self):
        return self.settings.get(
            "csp_report_uri",
            url_path_join(
                self.settings.get("hub_base_url", "/hub"), "security/csp-report"
            ),
        )

    @property
    def template_namespace(self):
        user = self.get_current_user()
        return dict(
            prefix=self.base_url,
            user=user,
            login_url=self.settings["login_url"],
            logout_url=self.settings["logout_url"],
            static_url=self.static_url,
            version_hash=self.version_hash,
        )

    def finish(self, *args, **kwargs):
        return super(JupyterHubBaseHandler, self).finish(*args, **kwargs)

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
