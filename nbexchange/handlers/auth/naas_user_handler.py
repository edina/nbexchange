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

        # TODO this _ to - transformation is unfortunate but the alternatives are also bad
        # Due to changes in the API in aug/sept 2020 the username was transformed for the UI to appear
        # as 1-xyz instead of 1_xyz. This was due to K8S only supporting DNS compatible characters for some reasources
        # which _ isn't. The other nice benefit was to get rid of %2F in places. Unfortunately nbexchange used this
        # same API and its username format was changed at the same time.
        # The username is used in the path to user assignment submissions and is recorded in the nbexchange database
        # and on the NFS filesystem. Changing this back would require these usernames are reformatted from their
        # 1-xyz format back to 1_xyz
        transformed_username = result["username"].replace("_", "-", 1)

        return {
            "name": transformed_username,
            "course_id": result["n_cid"],
            "course_title": result["n_cnm"],
            "course_role": result["n_rl"],
            "org_id": result["n_oid"],
        }
