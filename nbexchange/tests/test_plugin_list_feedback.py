import logging
import os
import shutil
from copy import deepcopy  # dict.copy only copies the top level!
from os.path import basename
from shutil import copyfile
from unittest.mock import ANY

import pytest
from mock import patch
from nbgrader.coursedir import CourseDirectory

from nbexchange.plugin import Exchange, ExchangeList
from nbexchange.tests.utils import (
    get_feedback_file,
    mock_api_fetched_assign_a_0_seconds,
    mock_api_release_feedback_assign_a_0_seconds,
    mock_api_released_assign_a_0_seconds,
    mock_api_submit_assign_a_0_seconds,
    root_notebook_name,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

# notebook 1
notebook1_filename = os.path.join(os.path.dirname(__file__), "data", f"{root_notebook_name}.ipynb")
notebook1_file = get_feedback_file(notebook1_filename)
feedback1_filename = os.path.join(os.path.dirname(__file__), "data", f"{root_notebook_name}.html")
feedback1_file = get_feedback_file(feedback1_filename)

# notebook 2
notebook2_filename = os.path.join(os.path.dirname(__file__), "data", f"{root_notebook_name}-2.ipynb")
notebook2_file = get_feedback_file(notebook2_filename)
feedback2_filename = os.path.join(os.path.dirname(__file__), "data", f"{root_notebook_name}-2.html")
feedback2_file = get_feedback_file(feedback2_filename)

# notebook 3
notebook3_filename = os.path.join(os.path.dirname(__file__), "data", f"{root_notebook_name}-3.ipynb")
notebook3_file = get_feedback_file(notebook3_filename)
feedback3_filename = os.path.join(os.path.dirname(__file__), "data", f"{root_notebook_name}-3.html")
feedback3_file = get_feedback_file(feedback3_filename)


@pytest.mark.gen_test
def test_list_no_submitted_records(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.ExchangeList.inbound = True

    plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    release_1 = deepcopy(mock_api_released_assign_a_0_seconds)
    fetch_1 = deepcopy(mock_api_fetched_assign_a_0_seconds)

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
                            fetch_1,
                            release_1,
                        ],
                    }
                ),
            },
        )

    with patch.object(Exchange, "api_request", side_effect=api_request):
        called = plugin.start()
        assert called == []


@pytest.mark.gen_test
def test_list_submit_one(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.ExchangeList.inbound = True

    plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    submit_1 = deepcopy(mock_api_submit_assign_a_0_seconds)

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
                        "value": [submit_1],
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
                "status": "submitted",
                "submissions": [
                    {
                        "assignment_id": "assign_a",
                        "course_id": "no_course",
                        "feedback_updated": False,
                        "has_exchange_feedback": False,
                        "has_local_feedback": False,
                        "path": "submitted/1/assign_a/1/foo",
                        "status": "submitted",
                        "student_id": 1,
                        "local_feedback_path": None,
                        "notebooks": [
                            {
                                "feedback_timestamp": None,
                                "feedback_updated": False,
                                "has_exchange_feedback": False,
                                "has_local_feedback": False,
                                "local_feedback_path": None,
                                "notebook_id": f"{root_notebook_name}",
                            }
                        ],
                        "timestamp": "2020-01-01 00:00:00.000000 UTC",
                    }
                ],
            }
        ]


# Note there is 1 student/assignment set, and the repeat is in the "submissions" list
@pytest.mark.gen_test
def test_list_submit_several_submissions(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.ExchangeList.inbound = True

    plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    submit_1 = deepcopy(mock_api_submit_assign_a_0_seconds)
    submit_2 = deepcopy(mock_api_submit_assign_a_0_seconds)
    submit_3 = deepcopy(mock_api_submit_assign_a_0_seconds)
    submit_2["timestamp"] = "2020-01-01 00:00:01.000000 UTC"
    submit_3["timestamp"] = "2020-01-01 00:00:02.000000 UTC"

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
                            submit_1,
                            submit_2,
                            submit_3,
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
                "status": "submitted",
                "submissions": [
                    {
                        "assignment_id": "assign_a",
                        "course_id": "no_course",
                        "feedback_updated": False,
                        "has_exchange_feedback": False,
                        "has_local_feedback": False,
                        "path": "submitted/1/assign_a/1/foo",
                        "status": "submitted",
                        "student_id": 1,
                        "local_feedback_path": None,
                        "notebooks": [
                            {
                                "feedback_timestamp": None,
                                "feedback_updated": False,
                                "has_exchange_feedback": False,
                                "has_local_feedback": False,
                                "local_feedback_path": None,
                                "notebook_id": f"{root_notebook_name}",
                            }
                        ],
                        "timestamp": "2020-01-01 00:00:00.000000 UTC",
                    },
                    {
                        "assignment_id": "assign_a",
                        "course_id": "no_course",
                        "feedback_updated": False,
                        "has_exchange_feedback": False,
                        "has_local_feedback": False,
                        "path": "submitted/1/assign_a/1/foo",
                        "status": "submitted",
                        "student_id": 1,
                        "local_feedback_path": None,
                        "notebooks": [
                            {
                                "feedback_timestamp": None,
                                "feedback_updated": False,
                                "has_exchange_feedback": False,
                                "has_local_feedback": False,
                                "local_feedback_path": None,
                                "notebook_id": f"{root_notebook_name}",
                            }
                        ],
                        "timestamp": "2020-01-01 00:00:01.000000 UTC",
                    },
                    {
                        "assignment_id": "assign_a",
                        "course_id": "no_course",
                        "feedback_updated": False,
                        "has_exchange_feedback": False,
                        "has_local_feedback": False,
                        "path": "submitted/1/assign_a/1/foo",
                        "status": "submitted",
                        "student_id": 1,
                        "local_feedback_path": None,
                        "notebooks": [
                            {
                                "feedback_timestamp": None,
                                "feedback_updated": False,
                                "has_exchange_feedback": False,
                                "has_local_feedback": False,
                                "local_feedback_path": None,
                                "notebook_id": f"{root_notebook_name}",
                            }
                        ],
                        "timestamp": "2020-01-01 00:00:02.000000 UTC",
                    },
                ],
            }
        ]


@pytest.mark.gen_test
def test_list_feedback_available(plugin_config, tmpdir):
    try:
        course_code = "no_course"
        assignment_id = "assign_a"
        timestamp = "2020-01-01 00:02:00.000000 UTC"
        plugin_config.CourseDirectory.course_id = course_code
        plugin_config.CourseDirectory.assignment_id = assignment_id

        plugin_config.ExchangeList.inbound = True

        my_feedback_dir = os.path.join(assignment_id, "feedback", timestamp)
        os.makedirs(my_feedback_dir, exist_ok=True)
        copyfile(
            feedback1_filename,
            os.path.join(
                my_feedback_dir,
                basename(feedback1_filename),
            ),
        )

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

        submit_1 = deepcopy(mock_api_submit_assign_a_0_seconds)
        submit_1["timestamp"] = timestamp
        submit_1["notebooks"][0]["has_exchange_feedback"] = True
        submit_1["notebooks"][0]["feedback_timestamp"] = timestamp

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
                                submit_1,
                            ],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            assert called == [
                {
                    "assignment_id": assignment_id,
                    "course_id": course_code,
                    "student_id": 1,
                    "status": "submitted",
                    "submissions": [
                        {
                            "assignment_id": assignment_id,
                            "course_id": course_code,
                            "path": "submitted/1/assign_a/1/foo",
                            "status": "submitted",
                            "student_id": 1,
                            "notebooks": [
                                {
                                    "feedback_timestamp": timestamp,
                                    "has_exchange_feedback": True,
                                    "has_local_feedback": True,
                                    "local_feedback_path": f"{assignment_id}/feedback/{timestamp}/{root_notebook_name}.html",  # noqa: E501
                                    "feedback_updated": False,
                                    "notebook_id": root_notebook_name,
                                }
                            ],
                            "timestamp": timestamp,
                            "feedback_updated": False,
                            "has_exchange_feedback": True,
                            "has_local_feedback": True,
                            "local_feedback_path": f"{assignment_id}/feedback/{timestamp}",
                        }
                    ],
                }
            ]

    finally:
        shutil.rmtree(assignment_id)


@pytest.mark.gen_test
def test_list_feedback_available_with_path_includes_course(plugin_config, tmpdir):
    try:
        course_code = "no_course"
        assignment_id = "assign_a"
        timestamp = "2020-01-01 00:02:00.000000 UTC"
        plugin_config.CourseDirectory.course_id = course_code
        plugin_config.CourseDirectory.assignment_id = assignment_id

        plugin_config.ExchangeList.inbound = True
        plugin_config.Exchange.path_includes_course = True

        my_feedback_dir = os.path.join(course_code, assignment_id, "feedback", timestamp)
        os.makedirs(my_feedback_dir, exist_ok=True)
        copyfile(
            feedback1_filename,
            os.path.join(
                my_feedback_dir,
                basename(feedback1_filename),
            ),
        )

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

        submit_1 = deepcopy(mock_api_submit_assign_a_0_seconds)
        submit_1["timestamp"] = timestamp
        submit_1["notebooks"][0]["has_exchange_feedback"] = True
        submit_1["notebooks"][0]["feedback_timestamp"] = timestamp

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
                                submit_1,
                            ],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            called = plugin.start()
            assert called == [
                {
                    "assignment_id": assignment_id,
                    "course_id": course_code,
                    "student_id": 1,
                    "status": "submitted",
                    "submissions": [
                        {
                            "assignment_id": assignment_id,
                            "course_id": course_code,
                            "path": "submitted/1/assign_a/1/foo",
                            "status": "submitted",
                            "student_id": 1,
                            "notebooks": [
                                {
                                    "feedback_timestamp": timestamp,
                                    "has_exchange_feedback": True,
                                    "has_local_feedback": True,
                                    "local_feedback_path": f"{my_feedback_dir}/{root_notebook_name}.html",
                                    "feedback_updated": False,
                                    "notebook_id": root_notebook_name,
                                }
                            ],
                            "timestamp": timestamp,
                            "feedback_updated": False,
                            "has_exchange_feedback": True,
                            "has_local_feedback": True,
                            "local_feedback_path": my_feedback_dir,
                        }
                    ],
                }
            ]
    finally:
        shutil.rmtree(course_code)


# This is a complicated one: 5 submissions, feedback generated for #2 & #4, but #4 hasn't been
# fetched yet
# on-disk feedback to match the api return
@pytest.mark.gen_test
def test_list_with_5_submit_and_3_feedback(plugin_config, tmpdir):
    try:
        course_code = "no_course"
        assignment_id = "assign_a"
        plugin_config.CourseDirectory.course_id = course_code
        plugin_config.CourseDirectory.assignment_id = assignment_id

        plugin_config.ExchangeList.inbound = True
        plugin_config.Exchange.path_includes_course = True

        submit_timestamp1 = "2020-01-01 00:00:01.000000 UTC"
        submit_timestamp2 = "2020-01-01 00:00:02.000000 UTC"
        submit_timestamp3 = "2020-01-01 00:00:03.000000 UTC"
        submit_timestamp4 = "2020-01-01 00:00:04.000000 UTC"
        submit_timestamp5 = "2020-01-01 00:00:05.000000 UTC"
        assignment_dir = f"{course_code}/{assignment_id}"
        feedback_dir1 = f"{assignment_dir}/feedback/{submit_timestamp2}"

        os.makedirs(assignment_dir, exist_ok=True)
        copyfile(notebook1_filename, os.path.join(assignment_dir, basename(notebook1_filename)))
        copyfile(notebook2_filename, os.path.join(assignment_dir, basename(notebook2_filename)))

        # two feedback files collected for the first round, but not the 2nd
        os.makedirs(feedback_dir1, exist_ok=True)
        copyfile(feedback1_filename, os.path.join(feedback_dir1, basename(feedback1_filename)))
        copyfile(feedback2_filename, os.path.join(feedback_dir1, basename(feedback2_filename)))

        plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

        release_1 = deepcopy(mock_api_released_assign_a_0_seconds)
        fetch_1 = deepcopy(mock_api_fetched_assign_a_0_seconds)

        submit_1 = deepcopy(mock_api_submit_assign_a_0_seconds)
        submit_2 = deepcopy(mock_api_submit_assign_a_0_seconds)
        submit_3 = deepcopy(mock_api_submit_assign_a_0_seconds)
        submit_4 = deepcopy(mock_api_submit_assign_a_0_seconds)
        submit_5 = deepcopy(mock_api_submit_assign_a_0_seconds)

        submit_1["timestamp"] = submit_timestamp1
        submit_2["timestamp"] = submit_timestamp2
        submit_2["notebooks"][0]["feedback_timestamp"] = submit_timestamp2
        submit_2["notebooks"][0]["has_exchange_feedback"] = True
        submit_3["timestamp"] = submit_timestamp3
        submit_4["timestamp"] = submit_timestamp4
        submit_4["notebooks"][0]["feedback_timestamp"] = submit_timestamp4
        submit_4["notebooks"][0]["has_exchange_feedback"] = True
        submit_5["timestamp"] = submit_timestamp5

        feedback_1 = deepcopy(mock_api_release_feedback_assign_a_0_seconds)
        feedback_2 = deepcopy(mock_api_release_feedback_assign_a_0_seconds)
        feedback_1["timestamp"] = submit_timestamp2
        feedback_1["notebooks"][0]["feedback_timestamp"] = submit_timestamp2
        feedback_1["notebooks"][0]["has_exchange_feedback"] = True
        feedback_2["timestamp"] = submit_timestamp4
        feedback_2["notebooks"][0]["feedback_timestamp"] = submit_timestamp4
        feedback_2["notebooks"][0]["has_exchange_feedback"] = True

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
                                submit_1,
                                submit_2,
                                feedback_1,
                                submit_3,
                                submit_4,
                                feedback_2,
                                submit_5,
                            ],
                        }
                    ),
                },
            )

        with patch.object(Exchange, "api_request", side_effect=api_request):
            plugin.inbound = True
            called = plugin.start()

            assert called == [
                {
                    "assignment_id": "assign_a",
                    "course_id": "no_course",
                    "status": "submitted",
                    "student_id": 1,
                    "submissions": [
                        {
                            "assignment_id": "assign_a",
                            "course_id": "no_course",
                            "feedback_updated": False,
                            "has_exchange_feedback": False,
                            "has_local_feedback": False,
                            "local_feedback_path": None,
                            "notebooks": [
                                {
                                    "feedback_timestamp": None,
                                    "feedback_updated": False,
                                    "has_exchange_feedback": False,
                                    "has_local_feedback": False,
                                    "local_feedback_path": None,
                                    "notebook_id": "assignment-0.6",
                                },
                            ],
                            "path": ANY,
                            "status": "submitted",
                            "student_id": 1,
                            "timestamp": submit_timestamp1,
                        },
                        {
                            "assignment_id": "assign_a",
                            "course_id": "no_course",
                            "feedback_updated": False,
                            "has_exchange_feedback": True,
                            "has_local_feedback": True,
                            "local_feedback_path": f"{assignment_dir}/feedback/{submit_timestamp2}",
                            "notebooks": [
                                {
                                    "feedback_timestamp": submit_timestamp2,
                                    "feedback_updated": False,
                                    "has_exchange_feedback": True,
                                    "has_local_feedback": True,
                                    "local_feedback_path": f"{assignment_dir}/feedback/{submit_timestamp2}/assignment-0.6.html",  # noqa: E501
                                    "notebook_id": "assignment-0.6",
                                },
                            ],
                            "path": ANY,
                            "status": "submitted",
                            "student_id": 1,
                            "timestamp": submit_timestamp2,
                        },
                        {
                            "assignment_id": "assign_a",
                            "course_id": "no_course",
                            "feedback_updated": False,
                            "has_exchange_feedback": False,
                            "has_local_feedback": False,
                            "local_feedback_path": None,
                            "notebooks": [
                                {
                                    "feedback_timestamp": None,
                                    "feedback_updated": False,
                                    "has_exchange_feedback": False,
                                    "has_local_feedback": False,
                                    "local_feedback_path": None,
                                    "notebook_id": "assignment-0.6",
                                },
                            ],
                            "path": ANY,
                            "status": "submitted",
                            "student_id": 1,
                            "timestamp": submit_timestamp3,
                        },
                        {
                            "assignment_id": "assign_a",
                            "course_id": "no_course",
                            "feedback_updated": False,
                            "has_exchange_feedback": True,
                            "has_local_feedback": False,
                            "local_feedback_path": None,
                            "notebooks": [
                                {
                                    "feedback_timestamp": submit_timestamp4,
                                    "feedback_updated": False,
                                    "has_exchange_feedback": True,
                                    "has_local_feedback": False,
                                    "local_feedback_path": None,
                                    "notebook_id": "assignment-0.6",
                                },
                            ],
                            "path": ANY,
                            "status": "submitted",
                            "student_id": 1,
                            "timestamp": submit_timestamp4,
                        },
                        {
                            "assignment_id": "assign_a",
                            "course_id": "no_course",
                            "feedback_updated": False,
                            "has_exchange_feedback": False,
                            "has_local_feedback": False,
                            "local_feedback_path": None,
                            "notebooks": [
                                {
                                    "feedback_timestamp": None,
                                    "feedback_updated": False,
                                    "has_exchange_feedback": False,
                                    "has_local_feedback": False,
                                    "local_feedback_path": None,
                                    "notebook_id": "assignment-0.6",
                                },
                            ],
                            "path": ANY,
                            "status": "submitted",
                            "student_id": 1,
                            "timestamp": submit_timestamp5,
                        },
                    ],
                }
            ]

    finally:
        shutil.rmtree(course_code)
