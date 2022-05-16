"""pytest fixtures for nbexchange"""
import logging
import os
from getpass import getuser

import pytest
from pytest_docker_tools import build, container
from tornado import ioloop
from traitlets.config.loader import PyFileConfigLoader

import nbexchange.models.users
from nbexchange.app import NbExchange
from nbexchange.database import Session

here = os.path.abspath(os.path.dirname(__file__))
root = os.path.join(here, os.pardir, os.pardir)

testing_config = os.path.join(here, "testing_config.py")
testing_plugin_config = os.path.join(here, "testing_plugin_config.py")
logger = logging.getLogger(__name__)

# global db session object
_db = None


@pytest.fixture
def io_loop(request):
    """Fix tornado-5 compatibility in pytest_tornado io_loop"""
    io_loop = ioloop.IOLoop()
    io_loop.make_current()

    def _close():
        io_loop.clear_current()
        io_loop.close(all_fds=True)

    request.addfinalizer(_close)
    return io_loop


@pytest.fixture(scope="session")
def _nbexchange_config():
    """Load the nbexchange configuration
    Currently separate from the app fixture
    so that it can have a different scope (only once per session).
    """
    cfg = PyFileConfigLoader(testing_config).load_config()

    return cfg


@pytest.fixture()
def plugin_config():
    cfg = PyFileConfigLoader(testing_plugin_config).load_config()

    return cfg


# Factory as fixture - see https://docs.pytest.org/en/latest/fixture.html#factories-as-fixtures
# This way we can test different database configurations, depending on the
# environment variables passed in
@pytest.fixture
def app(request, io_loop, _nbexchange_config):
    """Launch the NbExchange app"""
    nbexchange = NbExchange.instance(config=_nbexchange_config)
    nbexchange.initialize([])
    nbexchange.start(run_loop=False)
    # instantiating nbexchange configures this
    # override again

    def cleanup():
        nbexchange.stop()
        NbExchange.clear_instance()

    request.addfinalizer(cleanup)
    # convenience for accessing nbexchange in tests
    nbexchange.url = f"http://127.0.0.1:{nbexchange.port}{nbexchange.base_url}".rstrip("/")

    return nbexchange


@pytest.fixture(scope="session")
def db():
    """Get a db session"""
    _db = Session()  #
    user = nbexchange.models.users.User(name=getuser(), org_id=1)  # TODO: remove Magic number
    _db.add(user)
    _db.commit()
    return _db


# Docker images
nbexchange_image = build(path=".")
container = container(image="{nbexchange_image.id}", ports={"9000/tcp": None})
