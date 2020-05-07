import logging
import os

import pytest
import requests

from mock import patch

from nbexchange.plugin import ExchangeFetchFeedback, Exchange
from nbgrader.coursedir import CourseDirectory

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


def test_(plugin_config):
    plugin = ExchangeFetchFeedback(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    def api_request(*args, **kwargs):
        return type(
            "Response",
            (object,),
            {
                "status_code": 202,
                "headers": {"content-type": "text/json"},
                "json": lambda: {"success": True, "feedback": ""},
            },
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()
