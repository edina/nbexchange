import logging
import os
from pathlib import Path
from time import sleep
from unittest.mock import ANY
from urllib.parse import quote_plus

import pytest
from mock import patch
from nbgrader.utils import make_unique_key, notebook_hash

from nbexchange.handlers.base import BaseHandler
from nbexchange.tests.test_handlers_base import BaseTestHandlers
from nbexchange.tests.utils import (  # noqa: F401 "clear_database"
    async_requests,
    clear_database,
    get_files_dict,
    timestamp_format,
    tz,
    user_kiz_instructor,
    user_kiz_student,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


# These data elements get repeated below, fairly often
released_match = {
    "assignment_id": "assign_a",
    "course_id": "course_2",
    "notebooks": [
        {
            "feedback_timestamp": None,
            "feedback_updated": False,
            "has_exchange_feedback": False,
            "notebook_id": "assignment-0.6",
        },
        {
            "feedback_timestamp": None,
            "feedback_updated": False,
            "has_exchange_feedback": False,
            "notebook_id": "assignment-0.6-2",
        },
    ],
    "path": ANY,
    "status": "released",
    "student_id": 1,
    "timestamp": ANY,
}
fetched_match = {
    "assignment_id": "assign_a",
    "course_id": "course_2",
    "notebooks": [
        {
            "feedback_timestamp": None,
            "feedback_updated": False,
            "has_exchange_feedback": False,
            "notebook_id": "assignment-0.6",
        },
        {
            "feedback_timestamp": None,
            "feedback_updated": False,
            "has_exchange_feedback": False,
            "notebook_id": "assignment-0.6-2",
        },
    ],
    "path": ANY,
    "status": "fetched",
    "student_id": 1,
    "timestamp": ANY,
}
feedback_released_match = {
    "assignment_id": "assign_a",
    "course_id": "course_2",
    "notebooks": [
        {
            "feedback_timestamp": None,
            "feedback_updated": False,
            "has_exchange_feedback": False,
            "notebook_id": "assignment-0.6",
        },
        {
            "feedback_timestamp": None,
            "feedback_updated": False,
            "has_exchange_feedback": False,
            "notebook_id": "assignment-0.6-2",
        },
    ],
    "path": ANY,
    "status": "feedback_released",
    "student_id": 1,
    "timestamp": ANY,
}
submit_with_no_feedback_match = {
    "assignment_id": "assign_a",
    "course_id": "course_2",
    "notebooks": [
        {
            "feedback_timestamp": None,
            "feedback_updated": False,
            "has_exchange_feedback": False,
            "notebook_id": "assignment-0.6",
        },
        {
            "feedback_timestamp": None,
            "feedback_updated": False,
            "has_exchange_feedback": False,
            "notebook_id": "assignment-0.6-2",
        },
    ],
    "path": ANY,
    "status": "submitted",
    "student_id": 1,
    "timestamp": ANY,
}


class TestHandlersFetchFullCycle(BaseTestHandlers):

    def _filter_like_plugin(self, assignments):
        pass
        # Filter response as plugin would - "inbound" [aka submitted], and mapping to fetched feedback
        # [which we have done, that was the last action - so we'll fake it]
        assignment_list = []
        my_assignments = []
        for assignment in assignments:
            if assignment["status"] in ["released", "submitted"]:
                assignment_list.append(assignment)
        for assignment in assignment_list:
            if assignment["status"] == "submitted":
                local_feedback_path = None
                has_local_feedback = False
                for notebook in assignment["notebooks"]:
                    nb_timestamp = notebook["feedback_timestamp"]
                    if nb_timestamp:
                        local_feedback_path = f"assign_a/feedback/{nb_timestamp}"
                        has_local_feedback = True
                    notebook["has_local_feedback"] = has_local_feedback
                    notebook["local_feedback_path"] = local_feedback_path
                # Set assignment-level variables is any not the individual notebooks
                # have them
                if assignment["notebooks"]:
                    has_local_feedback = any([nb.get("has_local_feedback") for nb in assignment["notebooks"]])
                    has_exchange_feedback = any([nb["has_exchange_feedback"] for nb in assignment["notebooks"]])
                    feedback_updated = any([nb.get("feedback_updated") for nb in assignment["notebooks"]])
                else:
                    has_local_feedback = False
                    has_exchange_feedback = False
                    feedback_updated = False

                assignment["has_local_feedback"] = has_local_feedback
                assignment["has_exchange_feedback"] = has_exchange_feedback
                assignment["feedback_updated"] = feedback_updated
                if has_local_feedback:
                    assignment["local_feedback_path"] = assignment["notebooks"][0]["local_feedback_path"]
                else:
                    assignment["local_feedback_path"] = None
            my_assignments.append(assignment)
        return my_assignments

    # test actual rerurn data-structure for the "list" call after every action
    @pytest.mark.gen_test
    def test_list_datastructure(self, app, clear_database):  # noqa: F811
        # set up the file to be uploaded
        release_files, notebooks, timestamp = get_files_dict()
        # release & list
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            r = yield async_requests.post(
                app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
                data={"notebooks": notebooks},
                files=release_files,
            )
            r = yield async_requests.get(app.url + "/assignments?course_id=course_2")

        assert r.status_code == 200
        response_data = r.json()
        assert response_data["value"] == [
            released_match,
        ]

        # a student fetch & list
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
            r = yield async_requests.get(app.url + "/assignments?course_id=course_2")
        response_data = r.json()

        assert response_data["value"] == [
            released_match,
            fetched_match,
        ]

        # student submits & list
        # Note - we need to note _this_ timestamp to check it's being kept in the datastructure
        submit_timestamp = timestamp
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            r = yield async_requests.post(
                app.url + f"/submission?course_id=course_2&assignment_id=assign_a&timestamp={submit_timestamp}",
                files=release_files,
            )
            r = yield async_requests.get(app.url + "/assignments?course_id=course_2")
        response_data = r.json()

        assert response_data["value"] == [
            released_match,
            fetched_match,
            submit_with_no_feedback_match,
        ]

        # instructor collects & student list - should be no different to above
        submitted_response_data = response_data
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            collected_data = None
            r = yield async_requests.get(
                app.url + "/collections?course_id=course_2&assignment_id=assign_a"
            )  # Get the data we need to make test the call we want to make
            response_data = r.json()
            collected_data = response_data["value"][0]
            r = yield async_requests.get(
                app.url
                + f"/collection?course_id={collected_data['course_id']}&assignment_id={collected_data['assignment_id']}"  # noqa: E501 W503
            )
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            r = yield async_requests.get(app.url + "/assignments?course_id=course_2")

        assert r.status_code == 200
        response_data = r.json()
        assert response_data == submitted_response_data

        # instructor releases feedback & student list - should be listed available
        notebooks = ["assignment-0.6", "assignment-0.6-2"]
        html_files = [
            os.path.join(os.path.dirname(__file__), "data", f"{notebooks[0]}.html"),
            os.path.join(os.path.dirname(__file__), "data", f"{notebooks[1]}.html"),
        ]
        student_id = user_kiz_student["name"]
        for html_file in html_files:
            notebook_id = Path(html_file).stem
            unique_key = make_unique_key(
                "course_2",
                "assign_a",
                notebook_id,
                student_id,
                submit_timestamp,
            )
            checksum = notebook_hash(html_file, unique_key)
            with open(html_file) as feedback_file:
                feedback_data = {"feedback": ("feedback.html", feedback_file.read())}

            url = (
                f"/feedback?course_id={quote_plus('course_2')}"
                f"&assignment_id={quote_plus('assign_a')}"
                f"&notebook={quote_plus(notebook_id)}"
                f"&student={quote_plus(student_id)}"
                f"&timestamp={quote_plus(submit_timestamp)}"
                f"&checksum={quote_plus(checksum)}"
            )
            with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
                r = yield async_requests.post(app.url + url, files=feedback_data)
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            r = yield async_requests.get(app.url + "/assignments?course_id=course_2")

        assert r.status_code == 200
        response_data = r.json()

        # Adds *two* actions - feedback releases html files individually, and there are two assignments
        assert response_data["value"] == [
            released_match,
            fetched_match,
            {
                "assignment_id": "assign_a",
                "course_id": "course_2",
                "notebooks": [
                    {
                        "feedback_timestamp": submit_timestamp,
                        "feedback_updated": False,
                        "has_exchange_feedback": True,
                        "notebook_id": "assignment-0.6",
                    },
                    {
                        "feedback_timestamp": submit_timestamp,
                        "feedback_updated": False,
                        "has_exchange_feedback": True,
                        "notebook_id": "assignment-0.6-2",
                    },
                ],
                "path": ANY,
                "status": "submitted",
                "student_id": 1,
                "timestamp": ANY,
            },
            feedback_released_match,
            feedback_released_match,
        ]

        # student fetches feedback - assert timestamps match original submitted timestamp,
        # and compare those to those in list.submitted
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            r = yield async_requests.get(app.url + "/feedback?course_id=course_2&assignment_id=assign_a")
        assert r.status_code == 200
        response_data = r.json()
        fetched_feedback = {}
        for f in response_data["feedback"]:
            fetched_feedback[f["filename"]] = f["timestamp"]
            assert f["timestamp"] == submit_timestamp
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            r = yield async_requests.get(app.url + "/assignments?course_id=course_2")

        assert r.status_code == 200
        response_data = r.json()

        for action in response_data["value"]:
            if action["status"] != "submitted":
                continue
            for notebook in action["notebooks"]:
                assert notebook["feedback_timestamp"] == submit_timestamp

        # Filter response as plugin would - "inbound" [aka submitted], and mapping to fetched feedback
        # [which we have done, that was the last action - so we'll fake it]
        my_assignments = self._filter_like_plugin(response_data["value"])

        assert my_assignments == [
            released_match,
            {
                "assignment_id": "assign_a",
                "course_id": "course_2",
                "feedback_updated": False,
                "has_exchange_feedback": True,
                "has_local_feedback": True,
                "local_feedback_path": f"assign_a/feedback/{submit_timestamp}",
                "notebooks": [
                    {
                        "feedback_timestamp": submit_timestamp,
                        "feedback_updated": False,
                        "has_exchange_feedback": True,
                        "has_local_feedback": True,
                        "local_feedback_path": f"assign_a/feedback/{submit_timestamp}",
                        "notebook_id": "assignment-0.6",
                    },
                    {
                        "feedback_timestamp": submit_timestamp,
                        "feedback_updated": False,
                        "has_exchange_feedback": True,
                        "has_local_feedback": True,
                        "local_feedback_path": f"assign_a/feedback/{submit_timestamp}",
                        "notebook_id": "assignment-0.6-2",
                    },
                ],
                "path": ANY,
                "status": "submitted",
                "student_id": 1,
                "timestamp": ANY,
            },
        ]

    # assume submit, submit, feedback, submit, submit, feedback, submit
    # the list should match timestamps to submissions 2 & 4 only
    @pytest.mark.gen_test
    def test_feedback_maps_to_submissions(self, app, clear_database):  # noqa: F811
        release_files, notebooks, timestamp = get_files_dict()
        import datetime

        # release
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            r = yield async_requests.post(
                app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
                data={"notebooks": notebooks},
                files=release_files,
            )
        # a student fetch
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")

        # student submit twice, delay between them
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            timestamp = datetime.datetime.now(tz).strftime(timestamp_format)
            r = yield async_requests.post(
                app.url + f"/submission?course_id=course_2&assignment_id=assign_a&timestamp={timestamp}",
                files=release_files,
            )
            sleep(1)
            timestamp = datetime.datetime.now(tz).strftime(timestamp_format)
            r = yield async_requests.post(
                app.url + f"/submission?course_id=course_2&assignment_id=assign_a&timestamp={timestamp}",
                files=release_files,
            )

        # instructor collects
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            collected_data = None
            r = yield async_requests.get(
                app.url + "/collections?course_id=course_2&assignment_id=assign_a"
            )  # Get the data we need to make test the call we want to make
            response_data = r.json()
            collected_data = response_data["value"][0]
            r = yield async_requests.get(
                app.url
                + f"/collection?course_id={collected_data['course_id']}&assignment_id={collected_data['assignment_id']}"  # noqa: E501 W503
            )

        # instructor releases feedback
        notebooks = ["assignment-0.6", "assignment-0.6-2"]
        html_files = [
            os.path.join(os.path.dirname(__file__), "data", f"{notebooks[0]}.html"),
            os.path.join(os.path.dirname(__file__), "data", f"{notebooks[1]}.html"),
        ]
        student_id = user_kiz_student["name"]
        for html_file in html_files:
            notebook_id = Path(html_file).stem
            unique_key = make_unique_key(
                "course_2",
                "assign_a",
                notebook_id,
                student_id,
                timestamp,  # this is the last submitted timestamp
            )
            checksum = notebook_hash(html_file, unique_key)
            with open(html_file) as feedback_file:
                feedback_data = {"feedback": ("feedback.html", feedback_file.read())}

            url = (
                f"/feedback?course_id={quote_plus('course_2')}"
                f"&assignment_id={quote_plus('assign_a')}"
                f"&notebook={quote_plus(notebook_id)}"
                f"&student={quote_plus(student_id)}"
                f"&timestamp={quote_plus(timestamp)}"
                f"&checksum={quote_plus(checksum)}"
            )
            with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
                r = yield async_requests.post(app.url + url, files=feedback_data)

        # student submit twice, more delays....
        sleep(1)
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            timestamp = datetime.datetime.now(tz).strftime(timestamp_format)
            r = yield async_requests.post(
                app.url + f"/submission?course_id=course_2&assignment_id=assign_a&timestamp={timestamp}",
                files=release_files,
            )
            sleep(1)
            timestamp = datetime.datetime.now(tz).strftime(timestamp_format)
            r = yield async_requests.post(
                app.url + f"/submission?course_id=course_2&assignment_id=assign_a&timestamp={timestamp}",
                files=release_files,
            )

        # instructor collects
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            collected_data = None
            r = yield async_requests.get(
                app.url + "/collections?course_id=course_2&assignment_id=assign_a"
            )  # Get the data we need to make test the call we want to make
            response_data = r.json()
            collected_data = response_data["value"][0]
            r = yield async_requests.get(
                app.url
                + f"/collection?course_id={collected_data['course_id']}&assignment_id={collected_data['assignment_id']}"  # noqa: E501 W503
            )

        # instructor releases feedback
        notebooks = ["assignment-0.6", "assignment-0.6-2"]
        html_files = [
            os.path.join(os.path.dirname(__file__), "data", f"{notebooks[0]}.html"),
            os.path.join(os.path.dirname(__file__), "data", f"{notebooks[1]}.html"),
        ]
        student_id = user_kiz_student["name"]
        for html_file in html_files:
            notebook_id = Path(html_file).stem
            unique_key = make_unique_key(
                "course_2",
                "assign_a",
                notebook_id,
                student_id,
                timestamp,  # this is the last submitted timestamp
            )
            checksum = notebook_hash(html_file, unique_key)
            with open(html_file) as feedback_file:
                feedback_data = {"feedback": ("feedback.html", feedback_file.read())}

            url = (
                f"/feedback?course_id={quote_plus('course_2')}"
                f"&assignment_id={quote_plus('assign_a')}"
                f"&notebook={quote_plus(notebook_id)}"
                f"&student={quote_plus(student_id)}"
                f"&timestamp={quote_plus(timestamp)}"
                f"&checksum={quote_plus(checksum)}"
            )
            with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
                r = yield async_requests.post(app.url + url, files=feedback_data)

        # student submits number 5....
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            timestamp = datetime.datetime.now(tz).strftime(timestamp_format)
            r = yield async_requests.post(
                app.url + f"/submission?course_id=course_2&assignment_id=assign_a&timestamp={timestamp}",
                files=release_files,
            )

        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            r = yield async_requests.get(app.url + "/assignments?course_id=course_2")
        response_data = r.json()
        data = response_data["value"]

        # Check submissions & feedback_timestamps line up
        assert data[2]["status"] == "submitted"
        assert data[2]["notebooks"][0]["feedback_timestamp"] is None
        assert data[3]["status"] == "submitted"
        assert data[3]["notebooks"][0]["feedback_timestamp"] == data[3]["timestamp"]
        assert data[6]["status"] == "submitted"
        assert data[6]["notebooks"][0]["feedback_timestamp"] is None
        assert data[7]["status"] == "submitted"
        assert data[7]["notebooks"][0]["feedback_timestamp"] == data[7]["timestamp"]
        assert data[10]["status"] == "submitted"
        assert data[10]["notebooks"][0]["feedback_timestamp"] is None
        assert data[3]["timestamp"] != data[7]["timestamp"]

        def _test_assignment_feedback(assignment):
            if assignment["has_exchange_feedback"]:
                assert assignment["notebooks"][0]["has_exchange_feedback"] is True
                assert assignment["has_local_feedback"] is True
                assert assignment["notebooks"][0]["local_feedback_path"] == os.path.join(
                    "assign_a", "feedback", assignment["timestamp"]
                )
                assert assignment["local_feedback_path"] == assignment["notebooks"][0]["local_feedback_path"]

            else:
                assert assignment["local_feedback_path"] is None
                assert assignment["notebooks"][0]["feedback_timestamp"] is None
                assert assignment["notebooks"][0]["has_exchange_feedback"] is False

        # Filter response as plugin would - "inbound" [aka submitted], and mapping to fetched feedback
        # [which we have done, that was the last action - so we'll fake it]
        my_assignments = self._filter_like_plugin(data)

        # Check submissions & feedback_timestamps line up
        # Note we've cheated, and set it so local feeback always exists if released

        # no feedback
        _test_assignment_feedback(my_assignments[1])

        # with feedback
        _test_assignment_feedback(my_assignments[2])

        # no feedback
        _test_assignment_feedback(my_assignments[3])

        # with feedback
        _test_assignment_feedback(my_assignments[4])

        # no feedback
        _test_assignment_feedback(my_assignments[5])

    # assume submit, submit, feedback, submit, submit, feedback, submit
    # the list should match timestamps to submissions 2 & 4 only
    @pytest.mark.gen_test
    def test_feedback_does_not_maps_to_submissions_aka_old_stylee(self, app, clear_database):  # noqa: F811
        release_files, notebooks, timestamp = get_files_dict()
        import datetime

        # release
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            r = yield async_requests.post(
                app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
                data={"notebooks": notebooks},
                files=release_files,
            )
        # a student fetch
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")

        # student submit twice, delay between them
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            timestamp = datetime.datetime.now(tz).strftime(timestamp_format)
            r = yield async_requests.post(
                app.url + "/submission?course_id=course_2&assignment_id=assign_a",
                files=release_files,
            )
            sleep(1)
            timestamp = datetime.datetime.now(tz).strftime(timestamp_format)
            r = yield async_requests.post(
                app.url + "/submission?course_id=course_2&assignment_id=assign_a",
                files=release_files,
            )

        # instructor collects
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            collected_data = None
            r = yield async_requests.get(
                app.url + "/collections?course_id=course_2&assignment_id=assign_a"
            )  # Get the data we need to make test the call we want to make
            response_data = r.json()
            collected_data = response_data["value"][0]
            r = yield async_requests.get(
                app.url
                + f"/collection?course_id={collected_data['course_id']}&assignment_id={collected_data['assignment_id']}"  # noqa: E501 W503
            )

        # instructor releases feedback
        notebooks = ["assignment-0.6", "assignment-0.6-2"]
        html_files = [
            os.path.join(os.path.dirname(__file__), "data", f"{notebooks[0]}.html"),
            os.path.join(os.path.dirname(__file__), "data", f"{notebooks[1]}.html"),
        ]
        student_id = user_kiz_student["name"]
        for html_file in html_files:
            notebook_id = Path(html_file).stem
            unique_key = make_unique_key(
                "course_2",
                "assign_a",
                notebook_id,
                student_id,
                timestamp,  # this is the last submitted timestamp
            )
            checksum = notebook_hash(html_file, unique_key)
            with open(html_file) as feedback_file:
                feedback_data = {"feedback": ("feedback.html", feedback_file.read())}

            url = (
                f"/feedback?course_id={quote_plus('course_2')}"
                f"&assignment_id={quote_plus('assign_a')}"
                f"&notebook={quote_plus(notebook_id)}"
                f"&student={quote_plus(student_id)}"
                f"&timestamp={quote_plus(timestamp)}"
                f"&checksum={quote_plus(checksum)}"
            )
            with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
                r = yield async_requests.post(app.url + url, files=feedback_data)

        # student submit twice, more delays....
        sleep(1)
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            timestamp = datetime.datetime.now(tz).strftime(timestamp_format)
            r = yield async_requests.post(
                app.url + "/submission?course_id=course_2&assignment_id=assign_a&",
                files=release_files,
            )
            sleep(1)
            timestamp = datetime.datetime.now(tz).strftime(timestamp_format)
            r = yield async_requests.post(
                app.url + "/submission?course_id=course_2&assignment_id=assign_a",
                files=release_files,
            )

        # instructor collects
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
            collected_data = None
            r = yield async_requests.get(
                app.url + "/collections?course_id=course_2&assignment_id=assign_a"
            )  # Get the data we need to make test the call we want to make
            response_data = r.json()
            collected_data = response_data["value"][0]
            r = yield async_requests.get(
                app.url
                + f"/collection?course_id={collected_data['course_id']}&assignment_id={collected_data['assignment_id']}"  # noqa: E501 W503
            )

        # instructor releases feedback
        notebooks = ["assignment-0.6", "assignment-0.6-2"]
        html_files = [
            os.path.join(os.path.dirname(__file__), "data", f"{notebooks[0]}.html"),
            os.path.join(os.path.dirname(__file__), "data", f"{notebooks[1]}.html"),
        ]
        student_id = user_kiz_student["name"]
        for html_file in html_files:
            notebook_id = Path(html_file).stem
            unique_key = make_unique_key(
                "course_2",
                "assign_a",
                notebook_id,
                student_id,
                timestamp,  # this is the last submitted timestamp
            )
            checksum = notebook_hash(html_file, unique_key)
            with open(html_file) as feedback_file:
                feedback_data = {"feedback": ("feedback.html", feedback_file.read())}

            url = (
                f"/feedback?course_id={quote_plus('course_2')}"
                f"&assignment_id={quote_plus('assign_a')}"
                f"&notebook={quote_plus(notebook_id)}"
                f"&student={quote_plus(student_id)}"
                f"&timestamp={quote_plus(timestamp)}"
                f"&checksum={quote_plus(checksum)}"
            )
            with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
                r = yield async_requests.post(app.url + url, files=feedback_data)

        # student submits number 5....
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            timestamp = datetime.datetime.now(tz).strftime(timestamp_format)
            r = yield async_requests.post(
                app.url + "/submission?course_id=course_2&assignment_id=assign_a",
                files=release_files,
            )

        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
            r = yield async_requests.get(app.url + "/assignments?course_id=course_2")
        response_data = r.json()
        data = response_data["value"]

        # Old stylee: all submissions get the last released feedback
        assert data[2]["status"] == "submitted"
        assert isinstance(data[2]["notebooks"][0]["feedback_timestamp"], str)
        assert data[3]["status"] == "submitted"
        assert isinstance(data[3]["notebooks"][0]["feedback_timestamp"], str)
        assert data[6]["status"] == "submitted"
        assert isinstance(data[6]["notebooks"][0]["feedback_timestamp"], str)
        assert data[7]["status"] == "submitted"
        assert isinstance(data[7]["notebooks"][0]["feedback_timestamp"], str)
        assert data[10]["status"] == "submitted"
        assert isinstance(data[10]["notebooks"][0]["feedback_timestamp"], str)

        # old stylee - all feedback timestamps are the same value
        assert data[2]["notebooks"][0]["feedback_timestamp"] == data[3]["notebooks"][0]["feedback_timestamp"]
        assert data[3]["notebooks"][0]["feedback_timestamp"] == data[6]["notebooks"][0]["feedback_timestamp"]
        assert data[6]["notebooks"][0]["feedback_timestamp"] == data[7]["notebooks"][0]["feedback_timestamp"]
        assert data[7]["notebooks"][0]["feedback_timestamp"] == data[10]["notebooks"][0]["feedback_timestamp"]

        # old stylee - not of the feedback timestamps match the submitted timestamp
        assert data[2]["notebooks"][0]["feedback_timestamp"] != data[2]["timestamp"]
        assert data[3]["notebooks"][0]["feedback_timestamp"] != data[3]["timestamp"]
        assert data[6]["notebooks"][0]["feedback_timestamp"] != data[6]["timestamp"]
        assert data[7]["notebooks"][0]["feedback_timestamp"] != data[7]["timestamp"]
        assert data[10]["notebooks"][0]["feedback_timestamp"] != data[10]["timestamp"]

        # Assert that all submissions have a local feedback path of the last record
        def _test_assignment_feedback(assignment):
            assert assignment["notebooks"][0]["has_exchange_feedback"] is True
            assert assignment["has_local_feedback"] is True
            assert assignment["notebooks"][0]["local_feedback_path"] == os.path.join(
                "assign_a", "feedback", assignment["notebooks"][0]["feedback_timestamp"]
            )
            assert assignment["local_feedback_path"] == my_assignments[5]["notebooks"][0]["local_feedback_path"]

        # Filter response as plugin would - "inbound" [aka submitted], and mapping to fetched feedback
        # [which we have done, that was the last action - so we'll fake it]
        my_assignments = self._filter_like_plugin(data)
        # old stylee - confirm submissions & feedback_timestamps do NOT line up

        # no feedback
        _test_assignment_feedback(my_assignments[1])

        # with feedback
        _test_assignment_feedback(my_assignments[2])

        # no feedback
        _test_assignment_feedback(my_assignments[3])

        # with feedback
        _test_assignment_feedback(my_assignments[4])

        # no feedback
        _test_assignment_feedback(my_assignments[5])
