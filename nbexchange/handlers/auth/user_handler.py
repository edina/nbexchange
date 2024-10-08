# 'abc' is 'Abstract base Class'
from abc import ABC, abstractmethod

from tornado import web


# Updated after looking at
# https://clamytoe.github.io/articles/2020/Mar/12/testing-abcs-with-abstract-methods-with-pytest/
class BaseUserHandler(ABC):
    @abstractmethod
    def get_current_user(self, request: web.RequestHandler) -> dict:
        """
        Get the currently logged in user based on the request handler that needs the user.
        The method should return a dict with the following values:
        {
            "name": username for user,
            "full_name": Actual name for the user (can be blank),
            "email": Optional email address (can be blank) - to feed into gradebook.db,
            "lms_user_id": Optional user_id for the LMS/VLE (can be blank) - to feed into gradebook.db,
            "course_id": the course the user is on,
            "course_title": the title of the course,
            "course_role": the role the user has on the course,
            "org_id": an id for the organisation the user belongs to,
        }

        Name, full_name, email, and lms_user_id are all used by nbgrader

        :param request: The request that caused get_user to be called
        :return: the currently logged in user details
        """
        pass
