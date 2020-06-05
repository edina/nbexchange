import logging
import os
import sys

import pytest

from mock import patch

from nbexchange.plugin import ExchangeFetchFeedback, Exchange
from nbgrader.coursedir import CourseDirectory

from nbexchange.tests.utils import get_feedback_file

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


feedback_filename = sys.argv[0]  # ourself :)
feedback_file = get_feedback_file(feedback_filename)


@pytest.mark.gen_test
def test_fetch_feedback_dir_created(plugin_config, tmpdir):
    plugin_config.Exchange.assignment_dir = str(
        tmpdir.mkdir("feedback_test").realpath()
    )
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = "assign_1"

    assert not os.path.isdir(
        os.path.join(plugin_config.Exchange.assignment_dir, "1", "feedback")
    )

    plugin = ExchangeFetchFeedback(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    def api_request(*args, **kwargs):
        assert args[0] == (f"feedback?assignment_id=assign_1")
        return type(
            "Response",
            (object,),
            {
                "status_code": 200,
                "headers": {"content-type": "text/json"},
                "json": lambda: {"success": True, "feedback": []},
            },
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()
        assert os.path.isdir(
            os.path.join(plugin_config.Exchange.assignment_dir, "assign_1", "feedback")
        )


@pytest.mark.gen_test
def test_fetch_feedback_dir_created_with_course_id(plugin_config, tmpdir):
    plugin_config.Exchange.assignment_dir = str(
        tmpdir.mkdir("feedback_test").realpath()
    )
    plugin_config.Exchange.path_includes_course = True
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = "assign_1"

    assert not os.path.isdir(
        os.path.join(
            plugin_config.Exchange.assignment_dir, "no_course", "1", "feedback"
        )
    )

    plugin = ExchangeFetchFeedback(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    def api_request(*args, **kwargs):
        assert args[0] == (f"feedback?assignment_id=assign_1")
        return type(
            "Response",
            (object,),
            {
                "status_code": 200,
                "headers": {"content-type": "text/json"},
                "json": lambda: {"success": True, "feedback": []},
            },
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()
        assert os.path.isdir(
            os.path.join(
                plugin_config.Exchange.assignment_dir,
                "no_course",
                "assign_1",
                "feedback",
            )
        )


@pytest.mark.gen_test
def test_fetch_feedback_fetch_normal(plugin_config, tmpdir):
    plugin_config.Exchange.assignment_dir = str(
        tmpdir.mkdir("feedback_test").realpath()
    )
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = "assign_1"

    plugin = ExchangeFetchFeedback(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    def api_request(*args, **kwargs):
        assert args[0] == (f"feedback?assignment_id=assign_1")
        assert "method" not in kwargs or kwargs.get("method").lower() == "get"
        return type(
            "Response",
            (object,),
            {
                "status_code": 200,
                "headers": {"content-type": "text/json"},
                "json": lambda: {
                    "success": True,
                    "feedback": [
                        {
                            "filename": "test_feedback.html",
                            "content": feedback_file,
                            "timestamp": "2020-01-01T00:00:00.100",
                        }
                    ],
                },
            },
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()
        assert os.path.exists(
            os.path.join(
                plugin.dest_path, "2020-01-01 00:00:00.100000", "test_feedback.html"
            )
        )


@pytest.mark.gen_test
def test_fetch_feedback_fetch_several_normal(plugin_config, tmpdir):
    plugin_config.Exchange.assignment_dir = str(
        tmpdir.mkdir("feedback_test").realpath()
    )
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = "assign_1"

    plugin = ExchangeFetchFeedback(
        coursedir=CourseDirectory(config=plugin_config), config=plugin_config
    )

    def api_request(*args, **kwargs):
        assert args[0] == (f"feedback?assignment_id=assign_1")
        assert "method" not in kwargs or kwargs.get("method").lower() == "get"
        return type(
            "Response",
            (object,),
            {
                "status_code": 200,
                "headers": {"content-type": "text/json"},
                "json": lambda: {
                    "success": True,
                    "feedback": [
                        {
                            "filename": "test_feedback1.html",
                            "content": feedback_file,
                            "timestamp": "2020-01-01T00:00:01",
                        },
                        {
                            "filename": "test_feedback2.html",
                            "content": feedback_file,
                            "timestamp": "2020-01-01T00:00:00",
                        },
                    ],
                },
            },
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()

        assert os.path.exists(
            os.path.join(
                plugin.dest_path, "2020-01-01 00:00:01.000000", "test_feedback1.html"
            )
        )
        assert os.path.exists(
            os.path.join(
                plugin.dest_path, "2020-01-01 00:00:00.000000", "test_feedback2.html"
            )
        )
