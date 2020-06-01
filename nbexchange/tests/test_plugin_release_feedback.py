import logging
import os
import sys

import pytest
import requests

from mock import patch

from nbexchange.plugin import ExchangeReleaseFeedback, Exchange
from nbgrader.coursedir import CourseDirectory

from nbexchange.tests.utils import get_feedback_file


logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


feedback_filename = sys.argv[0]  # ourself :)
feedback_file = get_feedback_file(feedback_filename)


def test_release_feedback_fetch_normal(plugin_config, tmpdir):
    plugin_config.Exchange.assignment_dir = str(
        tmpdir.mkdir("feedback_test").realpath()
    )

    plugin = ExchangeReleaseFeedback(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    def api_request(*args, **kwargs):
        return type(
            "Response",
            (object,),
            {
                "status_code": 202,
                "headers": {"content-type": "text/json"},
                "json": lambda: {
                    "success": True,
                    "feedback": [
                        {
                            "filename": "test_feedback.html",
                            "content": feedback_file,
                            "timestamp": "2020-01-01 00:00:00.0",
                        }
                    ],
                },
            },
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()


def test_release_feedback_fetch_several_normal(plugin_config, tmpdir):
    plugin_config.Exchange.assignment_dir = str(
        tmpdir.mkdir("feedback_test").realpath()
    )

    plugin = ExchangeReleaseFeedback(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    def api_request(*args, **kwargs):
        return type(
            "Response",
            (object,),
            {
                "status_code": 202,
                "headers": {"content-type": "text/json"},
                "json": lambda: {
                    "success": True,
                    "feedback": [
                        {
                            "filename": "test_feedback1.html",
                            "content": feedback_file,
                            "timestamp": "2020-01-01 00:00:00.0",
                        },
                        {
                            "filename": "test_feedback2.html",
                            "content": feedback_file,
                            "timestamp": "2020-01-01 00:00:00.0",
                        },
                    ],
                },
            },
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()
