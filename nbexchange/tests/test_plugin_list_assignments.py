import logging
import os
import shutil
from copy import deepcopy  # dict.copy only copies the top level!
from os.path import basename
from shutil import copyfile

import pytest
import requests
from mock import patch
from nbgrader.coursedir import CourseDirectory

from nbexchange.plugin import Exchange, ExchangeError, ExchangeList
from nbexchange.tests.utils import (
    get_feedback_file,
    mock_api_fetched_assign_a_0_seconds,
    mock_api_fetched_assign_b_0_seconds,
    mock_api_released_assign_a_0_seconds,
    mock_api_released_assign_b_0_seconds,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

notebook1_filename = os.path.join(os.path.dirname(__file__), "data", "assignment-0.6.ipynb")
notebook1_file = get_feedback_file(notebook1_filename)

notebook2_filename = os.path.join(os.path.dirname(__file__), "data", "assignment-0.6-2.ipynb")
notebook2_file = get_feedback_file(notebook2_filename)

# **WARNING**
# Python "a=b" for dictionaries means that a points to "b" - and updating "a" updates "b"
# use "a=b.copy()" to make a copy


# Released items come with feedback items.
@pytest.mark.gen_test
def test_list_normal(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"

    plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    release_1 = deepcopy(mock_api_released_assign_a_0_seconds)

    def api_request(*args, **kwargs):
        assert args[0] == ("assignments?course_id=no_course")
        assert "method" not in kwargs or kwargs.get("method").lower() == "get"
        return type(
            "Request",
            (object,),
            {
                "status_code": 200,
                "json": (
                    lambda: {
                        "success": True,
                        "value": [release_1],
                    }
                ),
            },
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()
        assert called == [
            {
                "assignment_id": "assign_a",
                "course_id": "no_course",
                "student_id": 1,
                "status": "released",
                "notebooks": [
                    {
                        "notebook_id": "assignment-0.6",
                        "has_exchange_feedback": False,
                        "feedback_updated": False,
                        "feedback_timestamp": None,
                    }
                ],
                "path": "released/1/assign_a/foo",
                "timestamp": "2020-01-01 00:00:00.000000 UTC",
            }
        ]


# two assignments, both get listed.
@pytest.mark.gen_test
def test_list_normal_multiple_assignments(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"

    plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    release_1 = deepcopy(mock_api_released_assign_a_0_seconds)
    release_2 = deepcopy(mock_api_released_assign_b_0_seconds)

    def api_request(*args, **kwargs):
        assert args[0] == ("assignments?course_id=no_course")
        assert "method" not in kwargs or kwargs.get("method").lower() == "get"
        return type(
            "Request",
            (object,),
            {
                "status_code": 200,
                "json": (
                    lambda: {
                        "success": True,
                        "value": [
                            release_1,
                            release_2,
                        ],
                    }
                ),
            },
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()
        assert called == [
            {
                "assignment_id": "assign_a",
                "course_id": "no_course",
                "student_id": 1,
                "status": "released",
                "notebooks": [
                    {
                        "notebook_id": "assignment-0.6",
                        "has_exchange_feedback": False,
                        "feedback_updated": False,
                        "feedback_timestamp": None,
                    }
                ],
                "path": "released/1/assign_a/foo",
                "timestamp": "2020-01-01 00:00:00.000000 UTC",
            },
            {
                "assignment_id": "assign_b",
                "course_id": "no_course",
                "student_id": 1,
                "status": "released",
                "notebooks": [
                    {
                        "notebook_id": "assignment-0.6-wrong",
                        "has_exchange_feedback": False,
                        "feedback_updated": False,
                        "feedback_timestamp": None,
                    }
                ],
                "path": "released/1/assign_b/foo",
                "timestamp": "2020-01-01 00:00:00.000000 UTC",
            },
        ]


# two assignments, 1 listed twice - we get the latests one
# This should never happen, but we want to be sure it's covered
@pytest.mark.gen_test
def test_list_normal_multiple_release_same_assignment(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

        release_1 = deepcopy(mock_api_released_assign_a_0_seconds)
        release_2 = deepcopy(mock_api_released_assign_b_0_seconds)
        release_3 = deepcopy(mock_api_released_assign_b_0_seconds)
        release_3["timestamp"] = "2020-01-01 00:00:02.000000 UTC"

        def api_request(*args, **kwargs):
            assert args[0] == ("assignments?course_id=no_course")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Request",
                (object,),
                {
                    "status_code": 200,
                    "json": (
                        lambda: {
                            "success": True,
                            "value": [release_1, release_2, release_3],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            assert called == [
                {
                    "assignment_id": "assign_a",
                    "course_id": "no_course",
                    "student_id": 1,
                    "status": "released",
                    "notebooks": [
                        {
                            "notebook_id": "assignment-0.6",
                            "has_exchange_feedback": False,
                            "feedback_updated": False,
                            "feedback_timestamp": None,
                        }
                    ],
                    "path": "released/1/assign_a/foo",
                    "timestamp": "2020-01-01 00:00:00.000000 UTC",
                },
                {
                    "assignment_id": "assign_b",
                    "course_id": "no_course",
                    "student_id": 1,
                    "status": "released",
                    "notebooks": [
                        {
                            "notebook_id": "assignment-0.6-wrong",
                            "has_exchange_feedback": False,
                            "feedback_updated": False,
                            "feedback_timestamp": None,
                        }
                    ],
                    "path": "released/1/assign_b/foo",
                    "timestamp": "2020-01-01 00:00:02.000000 UTC",
                },
            ]
    finally:
        pass


# Same as above, but the order in the api is reversed - so the plugin actually pays attention to timestamps
@pytest.mark.gen_test
def test_list_normal_multiple_released_same_assignment_bad_order(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

        release_1 = deepcopy(mock_api_released_assign_a_0_seconds)
        release_2 = deepcopy(mock_api_released_assign_b_0_seconds)
        release_3 = deepcopy(mock_api_released_assign_b_0_seconds)
        release_2["timestamp"] = "2020-01-01 00:00:02.000000 UTC"

        def api_request(*args, **kwargs):
            assert args[0] == ("assignments?course_id=no_course")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Request",
                (object,),
                {
                    "status_code": 200,
                    "json": (
                        lambda: {
                            "success": True,
                            "value": [release_1, release_2, release_3],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            assert called == [
                {
                    "assignment_id": "assign_a",
                    "course_id": "no_course",
                    "student_id": 1,
                    "status": "released",
                    "notebooks": [
                        {
                            "notebook_id": "assignment-0.6",
                            "has_exchange_feedback": False,
                            "feedback_updated": False,
                            "feedback_timestamp": None,
                        }
                    ],
                    "path": "released/1/assign_a/foo",
                    "timestamp": "2020-01-01 00:00:00.000000 UTC",
                },
                {
                    "assignment_id": "assign_b",
                    "course_id": "no_course",
                    "student_id": 1,
                    "status": "released",
                    "notebooks": [
                        {
                            "notebook_id": "assignment-0.6-wrong",
                            "has_exchange_feedback": False,
                            "feedback_updated": False,
                            "feedback_timestamp": None,
                        }
                    ],
                    "path": "released/1/assign_b/foo",
                    "timestamp": "2020-01-01 00:00:02.000000 UTC",
                },
            ]
    finally:
        pass


# a fetched item on disk should remove the "released" items in the list.
# Note that the timestamp is that of the 'released' record
@pytest.mark.gen_test
def test_list_fetched(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"

        os.makedirs("assign_a", exist_ok=True)
        copyfile(notebook1_filename, os.path.join("assign_a", basename(notebook1_filename)))

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

        release_1 = deepcopy(mock_api_released_assign_a_0_seconds)
        fetch_1 = deepcopy(mock_api_fetched_assign_a_0_seconds)
        fetch_1["timestamp"] = "2020-01-01 00:00:02.000000 UTC"

        def api_request(*args, **kwargs):
            assert args[0] == ("assignments?course_id=no_course")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Request",
                (object,),
                {
                    "status_code": 200,
                    "json": (
                        lambda: {
                            "success": True,
                            "value": [
                                release_1,
                                fetch_1,
                            ],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()

            assert called == [
                {
                    "assignment_id": "assign_a",
                    "course_id": "no_course",
                    "student_id": 1,
                    "status": "fetched",
                    "notebooks": [
                        {
                            "notebook_id": "assignment-0.6",
                            "has_exchange_feedback": False,
                            "feedback_updated": False,
                            "has_local_feedback": False,
                            "local_feedback_path": None,
                            "path": "./assign_a/assignment-0.6.ipynb",
                        }
                    ],
                    "path": "released/1/assign_a/foo",
                    "timestamp": "2020-01-01 00:00:00.000000 UTC",
                },
            ]
    finally:
        shutil.rmtree("assign_a")


# a fetched item on disk should remove the "released" items in the list
# Honour path_includes_course
@pytest.mark.gen_test
def test_list_fetched_with_path_includes_course(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"
        plugin_config.Exchange.path_includes_course = True

        os.makedirs("no_course/assign_a", exist_ok=True)
        copyfile(notebook1_filename, os.path.join("no_course", "assign_a", basename(notebook1_filename)))

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

        release_1 = deepcopy(mock_api_released_assign_a_0_seconds)
        fetch_1 = deepcopy(mock_api_fetched_assign_a_0_seconds)
        fetch_1["timestamp"] = "2020-01-01 00:00:02.000000 UTC"

        def api_request(*args, **kwargs):
            assert args[0] == ("assignments?course_id=no_course")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Request",
                (object,),
                {
                    "status_code": 200,
                    "json": (
                        lambda: {
                            "success": True,
                            "value": [
                                release_1,
                                fetch_1,
                            ],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()

            assert called == [
                {
                    "assignment_id": "assign_a",
                    "course_id": "no_course",
                    "student_id": 1,
                    "status": "fetched",
                    "notebooks": [
                        {
                            "notebook_id": "assignment-0.6",
                            "has_exchange_feedback": False,
                            "feedback_updated": False,
                            "has_local_feedback": False,
                            "local_feedback_path": None,
                            "path": "./no_course/assign_a/assignment-0.6.ipynb",
                        }
                    ],
                    "path": "released/1/assign_a/foo",
                    "timestamp": "2020-01-01 00:00:00.000000 UTC",
                },
            ]
    finally:
        shutil.rmtree("no_course")


# if an item has been fetched, a re-release is ignored
# (on-disk takes priority)
@pytest.mark.gen_test
def test_list_fetched_rerelease_ignored(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"

        os.makedirs("assign_a", exist_ok=True)
        copyfile(notebook1_filename, os.path.join("assign_a", basename(notebook1_filename)))

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)
        release_1 = deepcopy(mock_api_released_assign_a_0_seconds)
        fetch_1 = deepcopy(mock_api_fetched_assign_a_0_seconds)
        release_2 = deepcopy(mock_api_released_assign_a_0_seconds)
        release_2["timestamp"] = "2020-01-01 00:00:02.000000 UTC"

        def api_request(*args, **kwargs):
            assert args[0] == ("assignments?course_id=no_course")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Request",
                (object,),
                {
                    "status_code": 200,
                    "json": (
                        lambda: {
                            "success": True,
                            "value": [
                                release_1,
                                fetch_1,
                                release_2,
                            ],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            assert called == [
                {
                    "assignment_id": "assign_a",
                    "course_id": "no_course",
                    "student_id": 1,
                    "status": "fetched",
                    "notebooks": [
                        {
                            "notebook_id": "assignment-0.6",
                            "has_exchange_feedback": False,
                            "feedback_updated": False,
                            "has_local_feedback": False,
                            "local_feedback_path": None,
                            "path": "./assign_a/assignment-0.6.ipynb",
                        }
                    ],
                    "path": "released/1/assign_a/foo",
                    "timestamp": "2020-01-01 00:00:00.000000 UTC",
                },
            ]
    finally:
        shutil.rmtree("assign_a")


# multiple fetches in API still result in just one fetch in the list
@pytest.mark.gen_test
def test_list_multiple_fetch(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"

        os.makedirs("assign_a", exist_ok=True)
        copyfile(notebook1_filename, os.path.join("assign_a", basename(notebook1_filename)))

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

        release_1 = deepcopy(mock_api_released_assign_a_0_seconds)
        fetch_1 = deepcopy(mock_api_fetched_assign_a_0_seconds)
        fetch_2 = deepcopy(mock_api_fetched_assign_a_0_seconds)
        fetch_1["timestamp"] = "2020-01-01 00:00:02.000000 UTC"
        fetch_2["timestamp"] = "2020-01-01 00:00:02.000000 UTC"

        def api_request(*args, **kwargs):
            assert args[0] == ("assignments?course_id=no_course")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Request",
                (object,),
                {
                    "status_code": 200,
                    "json": (
                        lambda: {
                            "success": True,
                            "value": [
                                release_1,
                                fetch_1,
                                fetch_2,
                            ],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            # The timestamp is actually from the first 'released' item in the list
            assert called == [
                {
                    "assignment_id": "assign_a",
                    "course_id": "no_course",
                    "student_id": 1,
                    "status": "fetched",
                    "notebooks": [
                        {
                            "notebook_id": "assignment-0.6",
                            "has_exchange_feedback": False,
                            "feedback_updated": False,
                            "has_local_feedback": False,
                            "local_feedback_path": None,
                            "path": "./assign_a/assignment-0.6.ipynb",
                        }
                    ],
                    "path": "released/1/assign_a/foo",
                    "timestamp": "2020-01-01 00:00:00.000000 UTC",
                },
            ]
    finally:
        shutil.rmtree("assign_a")


# An on-disk assignment with no matching released record is ignored
@pytest.mark.gen_test
def test_list_fetch_without_release_ignored(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"

        os.makedirs("assign_1_3", exist_ok=True)
        copyfile(notebook1_filename, os.path.join("assign_1_3", basename(notebook1_filename)))

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

        release_1 = deepcopy(mock_api_released_assign_a_0_seconds)
        fetch_1 = deepcopy(mock_api_fetched_assign_b_0_seconds)

        def api_request(*args, **kwargs):
            assert args[0] == ("assignments?course_id=no_course")
            assert "method" not in kwargs or kwargs.get("method").lower() == "get"
            return type(
                "Request",
                (object,),
                {
                    "status_code": 200,
                    "json": (
                        lambda: {
                            "success": True,
                            "value": [
                                release_1,
                                fetch_1,
                            ],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            assert called == [
                {
                    "assignment_id": "assign_a",
                    "course_id": "no_course",
                    "student_id": 1,
                    "status": "released",
                    "notebooks": [
                        {
                            "notebook_id": "assignment-0.6",
                            "has_exchange_feedback": False,
                            "feedback_updated": False,
                            "feedback_timestamp": None,
                        }
                    ],
                    "path": "released/1/assign_a/foo",
                    "timestamp": "2020-01-01 00:00:00.000000 UTC",
                },
            ]
    finally:
        shutil.rmtree("assign_1_3")


@pytest.mark.gen_test
def test_list_does_timeout(plugin_config, caplog):
    plugin_config.CourseDirectory.course_id = "no_course"

    plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    def api_request(*args, **kwargs):
        raise requests.exceptions.Timeout

    expected_message = "Timed out trying to reach the exchange service to list available assignments."
    with patch.object(Exchange, "api_request", side_effect=api_request):
        with pytest.raises(ExchangeError, match=expected_message):
            plugin.start()
    assert expected_message in caplog.text
