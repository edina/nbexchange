"""pytest fixtures for nbexchange"""
import os
import pytest
import requests
import logging
from getpass import getuser
from tornado import ioloop
from tornado.httpclient import AsyncHTTPClient
from traitlets.config.loader import PyFileConfigLoader

from nbexchange import orm
from nbexchange.app import NbExchange

here = os.path.abspath(os.path.dirname(__file__))
root = os.path.join(here, os.pardir, os.pardir)

testing_config = os.path.join(here, "testing_config.py")
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

    # check if Hub is running and ready
    try:
        requests.get(cfg.NbExchange.hub_base_url, timeout=5, allow_redirects=False)
    except Exception as e:
        print(f"JupyterHub not available at {cfg.NbExchange.hub_base_url}: {e}")
        cfg.NbExchange.hub_url = ""
    else:
        print(f"JupyterHub available at {cfg.NbExchange.hub_base_url}")

    return cfg


@pytest.fixture
def app(request, io_loop, _nbexchange_config):
    """Launch the NbExchange app
    """
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
    nbexchange.url = f"http://127.0.0.1:{nbexchange.port}{nbexchange.base_url}".rstrip(
        "/"
    )

    return nbexchange


@pytest.fixture
def db():
    """Get a db session"""
    global _db
    if _db is None:
        _db = orm.new_session_factory("sqlite:///:memory:", log=logger)()
        user = orm.User(name=getuser(), org_id=1)  # TODO: remove Magic number
        _db.add(user)
        _db.commit()
    return _db
