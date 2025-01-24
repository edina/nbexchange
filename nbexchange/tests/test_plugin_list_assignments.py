import logging
import os
import shutil
from os.path import basename
from shutil import copyfile

import pytest
from mock import patch
from nbgrader.coursedir import CourseDirectory

from nbexchange.plugin import Exchange, ExchangeList
from nbexchange.tests.utils import get_feedback_file

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

notebook1_filename = os.path.join(os.path.dirname(__file__), "data", "assignment-0.6.ipynb")
notebook1_file = get_feedback_file(notebook1_filename)

notebook2_filename = os.path.join(os.path.dirname(__file__), "data", "assignment-0.6-2.ipynb")
notebook2_file = get_feedback_file(notebook2_filename)


# Released items come with feedback items.
@pytest.mark.gen_test
def test_list_normal(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"

    plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                            {
                                "assignment_id": "assign_1_1",
                                "student_id": 1,
                                "course_id": "no_course",
                                "status": "released",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": "assignment-0.6",
                                        "has_exchange_feedback": False,
                                        "feedback_updated": False,
                                        "feedback_timestamp": None,
                                    }
                                ],
                                "timestamp": "2020-01-01 00:00:00.0 00:00",
                            }
                        ],
                    }
                ),
            },
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()
        assert called == [
            {
                "assignment_id": "assign_1_1",
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
                "path": "",
                "timestamp": "2020-01-01 00:00:00.0 00:00",
            }
        ]


# two assignments, both get listed.
@pytest.mark.gen_test
def test_list_normal_multiple(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"

    plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                            {
                                "assignment_id": "assign_1_1",
                                "student_id": 1,
                                "course_id": "no_course",
                                "status": "released",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": "assignment-0.6",
                                        "has_exchange_feedback": False,
                                        "feedback_updated": False,
                                        "feedback_timestamp": None,
                                    }
                                ],
                                "timestamp": "2020-01-01 00:00:00.0 00:00",
                            },
                            {
                                "assignment_id": "assign_1_2",
                                "student_id": 1,
                                "course_id": "no_course",
                                "status": "released",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": "assignment-0.6-wrong",
                                        "has_exchange_feedback": False,
                                        "feedback_updated": False,
                                        "feedback_timestamp": None,
                                    }
                                ],
                                "timestamp": "2020-01-01 00:00:00.1 00:00",
                            },
                        ],
                    }
                ),
            },
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()
        assert called == [
            {
                "assignment_id": "assign_1_1",
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
                "path": "",
                "timestamp": "2020-01-01 00:00:00.0 00:00",
            },
            {
                "assignment_id": "assign_1_2",
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
                "path": "",
                "timestamp": "2020-01-01 00:00:00.1 00:00",
            },
        ]


# two assignments, 1 listed twice - we get the latests one
# This should never happen, but we want to be sure it's covered
@pytest.mark.gen_test
def test_list_normal_multiple_released(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                {
                                    "assignment_id": "assign_1_1",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "released",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                                },
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "released",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                                },
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "released",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6-2",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.2 00:00",
                                },
                            ],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            assert called == [
                {
                    "assignment_id": "assign_1_1",
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
                    "path": "",
                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                },
                {
                    "assignment_id": "assign_1_3",
                    "course_id": "no_course",
                    "student_id": 1,
                    "status": "released",
                    "notebooks": [
                        {
                            "notebook_id": "assignment-0.6-2",
                            "has_exchange_feedback": False,
                            "feedback_updated": False,
                            "feedback_timestamp": None,
                        }
                    ],
                    "path": "",
                    "timestamp": "2020-01-01 00:00:00.2 00:00",
                },
            ]
    finally:
        pass


# Same as above, but the order in the api is reversed
@pytest.mark.gen_test
def test_list_normal_multiple_released_duplicates(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                {
                                    "assignment_id": "assign_1_1",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "released",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                                },
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "released",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6-2",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.2 00:00",
                                },
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "released",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                                },
                            ],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            assert called == [
                {
                    "assignment_id": "assign_1_1",
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
                    "path": "",
                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                },
                {
                    "assignment_id": "assign_1_3",
                    "course_id": "no_course",
                    "student_id": 1,
                    "status": "released",
                    "notebooks": [
                        {
                            "notebook_id": "assignment-0.6-2",
                            "has_exchange_feedback": False,
                            "feedback_updated": False,
                            "feedback_timestamp": None,
                        }
                    ],
                    "path": "",
                    "timestamp": "2020-01-01 00:00:00.2 00:00",
                },
            ]
    finally:
        pass


# a fetched item on disk should remove the "released" items in the list
@pytest.mark.gen_test
def test_list_fetched(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"

        os.makedirs("assign_1_3", exist_ok=True)
        copyfile(notebook1_filename, os.path.join("assign_1_3", basename(notebook1_filename)))

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "released",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                                },
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "fetched",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                                },
                            ],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()

            assert called == [
                {
                    "assignment_id": "assign_1_3",
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
                            "path": "./assign_1_3/assignment-0.6.ipynb",
                        }
                    ],
                    "path": "",
                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                },
            ]
    finally:
        shutil.rmtree("assign_1_3")


# a fetched item on disk should remove the "released" items in the list
# Honour path_includes_course
@pytest.mark.gen_test
def test_list_fetched_with_path_includes_course(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"
        plugin_config.Exchange.path_includes_course = True

        os.makedirs(os.path.join("no_course", "assign_1_3"), exist_ok=True)
        copyfile(
            notebook1_filename,
            os.path.join("no_course", "assign_1_3", basename(notebook1_filename)),
        )

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "released",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                                },
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "fetched",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                                },
                            ],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            assert called == [
                {
                    "assignment_id": "assign_1_3",
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
                            "path": "./no_course/assign_1_3/assignment-0.6.ipynb",
                        }
                    ],
                    "path": "",
                    "timestamp": "2020-01-01 00:00:00.0 00:00",
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

        os.makedirs("assign_1_3", exist_ok=True)
        copyfile(notebook1_filename, os.path.join("assign_1_3", basename(notebook1_filename)))

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "released",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                                },
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "fetched",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                                },
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "released",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6-2",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:02.0 00:00",
                                },
                            ],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            # The timestamp is actually from the last 'released' item on the list
            assert called == [
                {
                    "assignment_id": "assign_1_3",
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
                            "path": "./assign_1_3/assignment-0.6.ipynb",
                        }
                    ],
                    "path": "",
                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                },
            ]
    finally:
        shutil.rmtree("assign_1_3")


# multiple fetches in API still result in just one fetch in the list
@pytest.mark.gen_test
def test_list_multiple_fetch(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"

        os.makedirs("assign_1_3", exist_ok=True)
        copyfile(notebook1_filename, os.path.join("assign_1_3", basename(notebook1_filename)))

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "released",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                                },
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "fetched",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:02.0 00:00",
                                },
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "fetched",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:04.0 00:00",
                                },
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
                    "assignment_id": "assign_1_3",
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
                            "path": "./assign_1_3/assignment-0.6.ipynb",
                        }
                    ],
                    "path": "",
                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                },
            ]
    finally:
        shutil.rmtree("assign_1_3")


# An on-disk assignment with no matching released record is ignored
@pytest.mark.gen_test
def test_list_fetch_without_release_ignored(plugin_config, tmpdir):
    try:
        plugin_config.CourseDirectory.course_id = "no_course"

        os.makedirs("assign_1_3", exist_ok=True)
        copyfile(notebook1_filename, os.path.join("assign_1_3", basename(notebook1_filename)))

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

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
                                {
                                    "assignment_id": "assign_1_1",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "released",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                                },
                                {
                                    "assignment_id": "assign_1_3",
                                    "student_id": 1,
                                    "course_id": "no_course",
                                    "status": "fetched",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": "assignment-0.6",
                                            "has_exchange_feedback": False,
                                            "feedback_updated": False,
                                            "feedback_timestamp": None,
                                        }
                                    ],
                                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                                },
                            ],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            assert called == [
                {
                    "assignment_id": "assign_1_1",
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
                    "path": "",
                    "timestamp": "2020-01-01 00:00:00.0 00:00",
                },
            ]
    finally:
        shutil.rmtree("assign_1_3")
