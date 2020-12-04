import os

import requests
import logging

from nbexchange.handlers.auth.user_handler import BaseUserHandler


class NaasUserHandler(BaseUserHandler):
    naas_url = os.environ.get("NAAS_URL", "https://127.0.0.1:8080")

    def get_current_user(self, request):
        # Call Django to Authenticate Our User
        api_endpoint = f"{self.naas_url}/api/users/current/"

        cookies = dict()
        # Pass through cookies
        for name in request.request.cookies:
            cookies[name] = request.get_cookie(name)

        try:
            r = requests.get(api_endpoint, cookies=cookies)
        except requests.exceptions.ConnectionError:
            logging.exception(f"Error connecting to {self.naas_url}")
            return None

        result = r.json()

        # self.log.debug("CODE: {} \nRESULT: {}".format(r.status_code, result))

        if r.status_code == 401:
            return None

        return {
            "name": result["username"],
            "course_id": result["course_code"],
            "course_title": result["course_title"],
            "course_role": result["role"],
            "org_id": result["organisation_id"],
        }
