import os

import jwt
import logging

from nbexchange.handlers.auth.user_handler import BaseUserHandler


class NaasUserHandler(BaseUserHandler):
    jwt_key = os.environ.get("SECRET_KEY")

    def get_current_user(self, request):
        cookies = dict()
        # Pass through cookies
        for name in request.request.cookies:
            cookies[name] = request.get_cookie(name)

        if "noteable_auth" not in cookies:
            logging.debug(
                f"No noteable_auth cookie found - got {','.join(request.request.cookies)}"
            )
            return None

        encoded = cookies["noteable_auth"]
        result = jwt.decode(encoded, self.jwt_key, algorithms=["HS256"])

        return {
            "name": result["username"],
            "course_id": result["n_cid"],
            "course_title": result["n_cnm"],
            "course_role": result["n_rl"],
            "org_id": result["n_oid"],
        }
