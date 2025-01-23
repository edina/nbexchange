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

root_notebook_name = "assignment-0.6"

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
                                "assignment_id": "assign_1_4",
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
                                        "exchange_path": None,
                                    }
                                ],
                                "timestamp": "2020-01-01 00:00:00.44 00:00",
                            },
                            {
                                "assignment_id": "assign_13",
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
                                        "exchange_path": None,
                                    }
                                ],
                                "timestamp": "2020-01-01 00:00:00.23 00:00",
                            },
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
                                "status": "submitted",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": f"{root_notebook_name}",
                                        "has_exchange_feedback": False,
                                        "feedback_updated": False,
                                        "feedback_timestamp": None,
                                        "exchange_path": None,
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
                "status": "submitted",
                "submissions": [
                    {
                        "assignment_id": "assign_1_1",
                        "course_id": "no_course",
                        "feedback_updated": False,
                        "has_exchange_feedback": False,
                        "has_local_feedback": False,
                        "path": "",
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
                                "exchange_path": None,
                            }
                        ],
                        "timestamp": "2020-01-01 00:00:00.0 00:00",
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
                                "status": "submitted",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": f"{root_notebook_name}",
                                        "has_exchange_feedback": False,
                                        "feedback_updated": False,
                                        "feedback_timestamp": None,
                                        "exchange_path": None,
                                    }
                                ],
                                "timestamp": "2020-01-01 00:00:00.0 00:00",
                            },
                            {
                                "assignment_id": "assign_1_1",
                                "student_id": 1,
                                "course_id": "no_course",
                                "status": "submitted",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": f"{root_notebook_name}",
                                        "has_exchange_feedback": False,
                                        "feedback_updated": False,
                                        "feedback_timestamp": None,
                                        "exchange_path": None,
                                    }
                                ],
                                "timestamp": "2020-01-01 00:01:00.1 00:00",
                            },
                            {
                                "assignment_id": "assign_1_1",
                                "student_id": 1,
                                "course_id": "no_course",
                                "status": "submitted",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": f"{root_notebook_name}",
                                        "has_exchange_feedback": False,
                                        "feedback_updated": False,
                                        "feedback_timestamp": None,
                                        "exchange_path": None,
                                    }
                                ],
                                "timestamp": "2020-01-01 00:02:00.1 00:00",
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
                "status": "submitted",
                "submissions": [
                    {
                        "assignment_id": "assign_1_1",
                        "course_id": "no_course",
                        "feedback_updated": False,
                        "has_exchange_feedback": False,
                        "has_local_feedback": False,
                        "path": "",
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
                                "exchange_path": None,
                            }
                        ],
                        "timestamp": "2020-01-01 00:00:00.0 00:00",
                    },
                    {
                        "assignment_id": "assign_1_1",
                        "course_id": "no_course",
                        "feedback_updated": False,
                        "has_exchange_feedback": False,
                        "has_local_feedback": False,
                        "path": "",
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
                                "exchange_path": None,
                            }
                        ],
                        "timestamp": "2020-01-01 00:01:00.1 00:00",
                    },
                    {
                        "assignment_id": "assign_1_1",
                        "course_id": "no_course",
                        "feedback_updated": False,
                        "has_exchange_feedback": False,
                        "has_local_feedback": False,
                        "path": "",
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
                                "exchange_path": None,
                            }
                        ],
                        "timestamp": "2020-01-01 00:02:00.1 00:00",
                    },
                ],
            }
        ]


# Note the student/assignment set preeats, not the "submissions" list
@pytest.mark.gen_test
def test_list_submit_multipule_students(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.ExchangeList.inbound = True

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
                                "status": "submitted",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": f"{root_notebook_name}",
                                        "has_exchange_feedback": False,
                                        "feedback_updated": False,
                                        "feedback_timestamp": None,
                                        "exchange_path": None,
                                    }
                                ],
                                "timestamp": "2020-01-01 00:00:00.0 00:00",
                            },
                            {
                                "assignment_id": "assign_1_1",
                                "student_id": 2,
                                "course_id": "no_course",
                                "status": "submitted",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": f"{root_notebook_name}",
                                        "has_exchange_feedback": False,
                                        "feedback_updated": False,
                                        "feedback_timestamp": None,
                                        "exchange_path": None,
                                    }
                                ],
                                "timestamp": "2020-01-01 00:01:00.0 00:00",
                            },
                            {
                                "assignment_id": "assign_1_1",
                                "student_id": 3,
                                "course_id": "no_course",
                                "status": "submitted",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": f"{root_notebook_name}",
                                        "has_exchange_feedback": False,
                                        "feedback_updated": False,
                                        "feedback_timestamp": None,
                                        "exchange_path": None,
                                    }
                                ],
                                "timestamp": "2020-01-01 00:02:00.0 00:00",
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
                "status": "submitted",
                "submissions": [
                    {
                        "assignment_id": "assign_1_1",
                        "course_id": "no_course",
                        "feedback_updated": False,
                        "has_exchange_feedback": False,
                        "has_local_feedback": False,
                        "path": "",
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
                                "exchange_path": None,
                            }
                        ],
                        "timestamp": "2020-01-01 00:00:00.0 00:00",
                    },
                ],
            },
            {
                "assignment_id": "assign_1_1",
                "course_id": "no_course",
                "student_id": 2,
                "status": "submitted",
                "submissions": [
                    {
                        "assignment_id": "assign_1_1",
                        "course_id": "no_course",
                        "feedback_updated": False,
                        "has_exchange_feedback": False,
                        "has_local_feedback": False,
                        "path": "",
                        "status": "submitted",
                        "student_id": 2,
                        "local_feedback_path": None,
                        "notebooks": [
                            {
                                "feedback_timestamp": None,
                                "feedback_updated": False,
                                "has_exchange_feedback": False,
                                "has_local_feedback": False,
                                "local_feedback_path": None,
                                "notebook_id": f"{root_notebook_name}",
                                "exchange_path": None,
                            }
                        ],
                        "timestamp": "2020-01-01 00:01:00.0 00:00",
                    },
                ],
            },
            {
                "assignment_id": "assign_1_1",
                "course_id": "no_course",
                "student_id": 3,
                "status": "submitted",
                "submissions": [
                    {
                        "assignment_id": "assign_1_1",
                        "course_id": "no_course",
                        "feedback_updated": False,
                        "has_exchange_feedback": False,
                        "has_local_feedback": False,
                        "path": "",
                        "status": "submitted",
                        "student_id": 3,
                        "local_feedback_path": None,
                        "notebooks": [
                            {
                                "feedback_timestamp": None,
                                "feedback_updated": False,
                                "has_exchange_feedback": False,
                                "has_local_feedback": False,
                                "local_feedback_path": None,
                                "notebook_id": f"{root_notebook_name}",
                                "exchange_path": None,
                            }
                        ],
                        "timestamp": "2020-01-01 00:02:00.0 00:00",
                    },
                ],
            },
        ]


# Note the student/assignment set repeats, not the "submissions" list
@pytest.mark.gen_test
def test_list_submit_multiple_assignments(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.ExchangeList.inbound = True

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
                                "status": "submitted",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": f"{root_notebook_name}",
                                        "has_exchange_feedback": False,
                                        "feedback_updated": False,
                                        "feedback_timestamp": None,
                                        "exchange_path": None,
                                    }
                                ],
                                "timestamp": "2020-01-01 00:00:00.0 00:00",
                            },
                            {
                                "assignment_id": "assign_1_2",
                                "student_id": 1,
                                "course_id": "no_course",
                                "status": "submitted",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": f"{root_notebook_name}",
                                        "has_exchange_feedback": False,
                                        "feedback_updated": False,
                                        "feedback_timestamp": None,
                                        "exchange_path": None,
                                    }
                                ],
                                "timestamp": "2020-01-01 00:01:00.0 00:00",
                            },
                            {
                                "assignment_id": "assign_1_3",
                                "student_id": 1,
                                "course_id": "no_course",
                                "status": "submitted",
                                "path": "",
                                "notebooks": [
                                    {
                                        "notebook_id": f"{root_notebook_name}",
                                        "has_exchange_feedback": False,
                                        "feedback_updated": False,
                                        "feedback_timestamp": None,
                                        "exchange_path": None,
                                    }
                                ],
                                "timestamp": "2020-01-01 00:02:00.0 00:00",
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
                "status": "submitted",
                "submissions": [
                    {
                        "assignment_id": "assign_1_1",
                        "course_id": "no_course",
                        "feedback_updated": False,
                        "has_exchange_feedback": False,
                        "has_local_feedback": False,
                        "path": "",
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
                                "exchange_path": None,
                            }
                        ],
                        "timestamp": "2020-01-01 00:00:00.0 00:00",
                    },
                ],
            },
            {
                "assignment_id": "assign_1_2",
                "course_id": "no_course",
                "student_id": 1,
                "status": "submitted",
                "submissions": [
                    {
                        "assignment_id": "assign_1_2",
                        "course_id": "no_course",
                        "feedback_updated": False,
                        "has_exchange_feedback": False,
                        "has_local_feedback": False,
                        "path": "",
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
                                "exchange_path": None,
                            }
                        ],
                        "timestamp": "2020-01-01 00:01:00.0 00:00",
                    },
                ],
            },
            {
                "assignment_id": "assign_1_3",
                "course_id": "no_course",
                "student_id": 1,
                "status": "submitted",
                "submissions": [
                    {
                        "assignment_id": "assign_1_3",
                        "course_id": "no_course",
                        "feedback_updated": False,
                        "has_exchange_feedback": False,
                        "has_local_feedback": False,
                        "path": "",
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
                                "exchange_path": None,
                            }
                        ],
                        "timestamp": "2020-01-01 00:02:00.0 00:00",
                    },
                ],
            },
        ]


@pytest.mark.gen_test
def test_list_feedback_available(plugin_config, tmpdir):
    try:
        course_code = "no_course"
        assignment_id = "assign_1_1"
        timestamp = "2020-01-01 00:02:00.2 00:00"
        plugin_config.CourseDirectory.course_id = course_code
        plugin_config.CourseDirectory.assignment_id = assignment_id

        plugin_config.ExchangeList.inbound = True

        my_feedback_dir = f"{assignment_id}/feedback/{timestamp}"
        os.makedirs(my_feedback_dir, exist_ok=True)
        copyfile(
            feedback1_filename,
            os.path.join(
                my_feedback_dir,
                basename(feedback1_filename),
            ),
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
                                    "assignment_id": assignment_id,
                                    "student_id": 1,
                                    "course_id": course_code,
                                    "status": "submitted",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": root_notebook_name,
                                            "has_exchange_feedback": True,
                                            "feedback_updated": False,
                                            "feedback_timestamp": timestamp,
                                            "exchange_path": None,
                                        }
                                    ],
                                    "timestamp": timestamp,
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
                    "assignment_id": assignment_id,
                    "course_id": course_code,
                    "student_id": 1,
                    "status": "submitted",
                    "submissions": [
                        {
                            "assignment_id": assignment_id,
                            "course_id": course_code,
                            "path": "",
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
                                    "exchange_path": None,
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
        assignment_id = "assign_1_1"
        plugin_config.CourseDirectory.course_id = course_code
        plugin_config.CourseDirectory.assignment_id = assignment_id

        plugin_config.ExchangeList.inbound = True
        plugin_config.Exchange.path_includes_course = True

        my_feedback_dir = f"{course_code}/{assignment_id}/feedback/2020-01-01 00:02:00.2 00:00"
        os.makedirs(my_feedback_dir, exist_ok=True)
        my_feedback_file = os.path.join(my_feedback_dir, basename(feedback1_filename))
        copyfile(feedback1_filename, my_feedback_file)

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
                                    "assignment_id": assignment_id,
                                    "student_id": 1,
                                    "course_id": course_code,
                                    "status": "submitted",
                                    "path": "",
                                    "notebooks": [
                                        {
                                            "notebook_id": root_notebook_name,
                                            "has_exchange_feedback": True,
                                            "feedback_updated": False,
                                            "feedback_timestamp": "2020-01-01 00:02:00.2 00:00",
                                            "exchange_path": my_feedback_file,
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
                    "assignment_id": assignment_id,
                    "course_id": course_code,
                    "student_id": 1,
                    "status": "submitted",
                    "submissions": [
                        {
                            "assignment_id": assignment_id,
                            "course_id": course_code,
                            "path": "",
                            "status": "submitted",
                            "student_id": 1,
                            "notebooks": [
                                {
                                    "feedback_timestamp": "2020-01-01 00:02:00.2 00:00",
                                    "has_exchange_feedback": True,
                                    "has_local_feedback": True,
                                    "local_feedback_path": f"{course_code}/{assignment_id}/feedback/2020-01-01 00:02:00.2 00:00/{root_notebook_name}.html",  # noqa: E501
                                    "feedback_updated": False,
                                    "notebook_id": root_notebook_name,
                                    "exchange_path": my_feedback_file,
                                }
                            ],
                            "timestamp": "2020-01-01 00:00:00.2 00:00",
                            "feedback_updated": False,
                            "has_exchange_feedback": True,
                            "has_local_feedback": True,
                            "local_feedback_path": f"{course_code}/{assignment_id}/feedback/2020-01-01 00:02:00.2 00:00",  # noqa: E501
                        }
                    ],
                }
            ]
    finally:
        shutil.rmtree(course_code)
