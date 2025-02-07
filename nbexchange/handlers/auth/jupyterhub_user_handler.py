import logging
import os

from jupyterhub.services.auth import HubAuth

from nbexchange.handlers.auth.user_handler import BaseUserHandler


class JupyterHubUserHandler(BaseUserHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hub_auth = HubAuth()
        self.course_id = os.environ["COURSE_ID"]

    def get_current_user(self, request):

        user_model = self.hub_auth.get_user(request)
        name = user_model.get("name")
        logging.debug(f"NaasUserHandler returning {name}")

        # Everyone gets access to the full exchange
        return {
            "name": name,
            "full_name": name,
            "course_id": self.course_id,
            "course_title": "cool course",
            "course_role": "Instructor",
            "org_id": 1,
        }
