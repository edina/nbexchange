import json

from nbgrader.auth import BaseAuthPlugin
from tornado import gen

from .exchange import Exchange


class NoteableEnvironmentError(Exception):
    pass


class NoteableApiError(Exception):
    pass


class NoteableAuthPlugin(BaseAuthPlugin):
    def query_exchange(self):
        """List all courses"""
        r = Exchange.api_request(self, "courses")  # use method in Exchange

        self.log.debug(f"Got back {r} when listing courses")

        try:
            response_data = r.json()
        except json.decoder.JSONDecodeError:
            self.log.error("Got back an invalid response when listing courses")
            return []

        self.log.debug(f"NoteableAuthPlugin.query_exchange - Got back {response_data} when listing courses")

        courses = list(map(lambda item: item["course_code"], response_data["value"]))
        return courses

    @gen.coroutine
    def get_student_courses(self):
        courses = []
        courses = self.query_exchange()
        return courses

    # add_student_to_course - not impliemnted, managed elsewhere
    # remove_student_from_course - not implimented, managed elsewhere
