# 'abc' is 'Abstract base Class'
from abc import ABC, abstractmethod
from tornado import web


class BaseUserHandler(ABC):
    @abstractmethod
    def get_current_user(self, request: web.RequestHandler):
        """
        Get the currently logged in user based on the request handler that needs the user.
        The method should return a dict with the following values:
        {
            "name": username for user,
            "course_id": the course the user is on,
            "course_title": the title of the course,
            "course_role": the role the user has on the course,
            "org_id": an id for the organisation the user belongs to,
        }

        :param request: The request that caused get_user to be called
        :return: the currently logged in user
        """
