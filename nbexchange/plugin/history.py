import json

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
        self.log.debug("Start getting api request")
        r = self.api_request(f'{"history"}')
        self.log.debug(f"Got back {r} when getting history")
        self.log.debug(type(r))
        try:
            self.log.debug("DO SOMETHING")
            self.log.debug(r)
            self.log.debug("ABOVE IS 'r' BELOW IS JSON()")
            #self.log.debug(r.json())
            #history = r.json()
        except json.decoder.JSONDecodeError:
            self.log.error(f'{"Got back an invalid response when getting history"}')
            return []

        return history["value"]

    def copy_files(self):
        pass

    def start(self):
        return self.query_exchange()
