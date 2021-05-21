import logging
from abc import ABCMeta

import pytest

from nbexchange.handlers.auth.user_handler import BaseUserHandler

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


@pytest.mark.gen_test
def test_base_abstract_class(app):
    BaseUserHandler.__abstractmethods__ = set()

    assert isinstance(BaseUserHandler, ABCMeta)
