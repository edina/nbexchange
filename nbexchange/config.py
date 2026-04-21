class Config:
    """
    A simple configuration class to hold global configuration values for nbexchange.
    This is not intended to be a full configuration management solution, but just a simple way to
    access configuration values across the codebase without having to pass them around everywhere.
    """

    _config = {}

    @staticmethod
    def initialize(**kwargs):
        Config._config.update(kwargs)

    @staticmethod
    def get(key):
        return Config._config.get(key)
