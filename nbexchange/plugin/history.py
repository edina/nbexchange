import glob
import json
import os
import re
import sys
from urllib.parse import quote, quote_plus

import nbgrader.exchange.abc as abc
from dateutil import parser
from traitlets import Bool, Unicode

from .exchange import Exchange


class ExchangeHistory(Exchange):
    def do_copy(self, src, dest):
        pass

    def init_src(self):
        pass

    def init_dest(self):
        pass

    # the list of assignments the exchange knows about
    history = []

    def query_exchange(self):
        """
        This queries the database for all the assignments for a course

        if self.inbound or self.cached are true, it returns all the 'submitted'
        items, else it returns all the 'released' ones.

        (it doesn't care about feedback or collected actions)
        """
        r = self.api_request(f"history")
        self.log.debug(f"Got back {r} when getting history")

        try:
            history = r.json()
        except json.decoder.JSONDecodeError:
            self.log.error(f"Got back an invalid response when getting history")
            return []

        return history["value"]

    def copy_files(self):
        pass

    def start(self):
        return self.query_exchange()
