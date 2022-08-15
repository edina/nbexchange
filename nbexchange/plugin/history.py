import json

from .exchange import Exchange


class ExchangeHistory(Exchange):

    def do_copy(self, src, dest):
        self.log.info("SERVER - Do Copy")
        pass

    def init_src(self):
        self.log.info("SERVER - Init src")
        pass

    def init_dest(self):
        self.log.info("SERVER - Init dest")
        pass

    # the list of assignments the exchange knows about
    history = []

    def query_exchange(self):
        self.log.info("query_exchange function call")
        self.log.info("Start getting api request")
        r = self.api_request(f'{"history"}')
        self.log.info(f"Got back {r} when getting history")
        self.log.info(type(r))
        try:
            self.log.info("DO SOMETHING")
            self.log.info(r)
            self.log.info("ABOVE IS 'r' BELOW IS JSON()")
            #self.log.debug(r.json())
            #history = r.json()
        except json.decoder.JSONDecodeError:
            self.log.error(f'{"Got back an invalid response when getting history"}')
            return []

        #return history["value"]
        pass

    def copy_files(self):
        self.log.info("SERVER - Copy files def")
        pass

    def start(self):
        self.log.info("SERVER - start def")
        return self.query_exchange()
