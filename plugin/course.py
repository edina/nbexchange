import glob
import json
import os
import sys

from .exchange import Exchange


class ExchangeCourse(Exchange):

    # the list of assignments the exchange knows about
    courses = []

    def query_exchange(self):
        """List of all courses"""
        r = self.api_request(f"courses")

        self.log.debug(f"Got back {r} when listing courses")

        try:
            courses = r.json()
        except json.decoder.JSONDecodeError:
            self.log.error(f"Got back an invalid response when listing courses")
            return []

        self.log.info(
            f"ExchangeList.query_exchange - Got back {courses} when listing courses"
        )

        return courses["value"]

    def start(self):
        return self.query_exchange()
