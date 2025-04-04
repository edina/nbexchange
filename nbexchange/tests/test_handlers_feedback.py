import base64
import os
import shutil
from datetime import datetime

import pytest
from mock import patch
from nbgrader.utils import make_unique_key, notebook_hash

from nbexchange.handlers.base import BaseHandler
from nbexchange.tests.utils import (  # noqa: F401 "clear_database"
    async_requests,
    clear_database,
    get_feedback_dict,
    get_files_dict,
    timestamp_format,
    tz,
    user_brobbere_student,
    user_kiz,
    user_kiz_instructor,
    user_kiz_student,
    user_lkihlman_instructor,
)

#################################
#
# Very Important Note
#
# The `clear_database` fixture removed all database records.
# In this suite of tests, we do that FOR EVERY TEST
# This means that every single test is run in isolation, and therefore will need to have the full Release, Fetch,
#   Submit steps done before the collection can be tested.
# (On the plus side, adding or changing a test will no longer affect those below)
#
# Note you also want to clear the exchange filestore too.... again, so files from 1 test don't throw another test
#
#################################

# set up the file to be uploaded
feedback_filename = os.path.join(os.path.dirname(__file__), "data", "assignment-0.6.html")
feedbacks = get_feedback_dict(feedback_filename)
feedback_base64 = base64.b64encode(open(feedback_filename).read().encode("utf-8"))
released_files, notebooks, timestamp = get_files_dict()


@pytest.mark.gen_test
def test_feedback_unauthenticated(app):
    """
    Require authenticated user
    """
    r = yield async_requests.get(app.url + "/feedback")
    assert r.status_code == 403


@pytest.mark.gen_test
def test_feedback_authenticated_no_params(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/feedback")
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Feedback call requires an assignment id and a course id"


@pytest.mark.gen_test
def test_feedback_authenticated_with_params(app, clear_database):  # noqa: F811
    assignment_id = "my_assignment"
    course_id = "my_course"

    url = f"/feedback?assignment_id={assignment_id}&course_id={course_id}"

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + url)

    assert r.status_code == 404


@pytest.mark.gen_test
def test_feedback_post_unauthenticated(app, clear_database):  # noqa: F811
    """
    Require authenticated user for posting
    """
    r = yield async_requests.post(app.url + "/feedback", files=feedbacks)
    assert r.status_code == 403


@pytest.mark.gen_test
def test_feedback_post_broken_nbex_user(app, clear_database, caplog):  # noqa: F811
    assignment_id = "my_assignment"

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id=course_2"
        f"&notebook=faked"
        f"&student=faked"
        f"&timestamp=faked"
        f"&checksum=faked"
    )

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz):  # No course details
        r = yield async_requests.post(app.url + url)
    assert r.status_code == 500
    assert "Both current_course ('None') and current_role ('None') must have values. User was '1-kiz'" in caplog.text


@pytest.mark.gen_test
def test_feedback_post_authenticated_no_params(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/feedback", files=feedbacks)
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."  # noqa: E501 W503
    )


@pytest.mark.gen_test
def test_feedback_post_authenticated_no_assignment_id(app, clear_database):  # noqa: F811
    url = "/feedback?course_id=faked&notebook=faked&student=faked&timestamp=faked&checksum=faked"

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."  # noqa: E501 W503
    )


@pytest.mark.gen_test
def test_feedback_post_authenticated_no_course_id(app, clear_database):  # noqa: F811
    assignment_id = "my_assignment"
    url = f"/feedback?assignment_id={assignment_id}&notebook=faked&student=faked&timestamp=faked&checksum=faked"

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."  # noqa: E501 W503
    )


@pytest.mark.gen_test
def test_feedback_post_authenticated_no_notebook(app, clear_database):  # noqa: F811
    assignment_id = "my_assignment"
    url = f"/feedback?assignment_id={assignment_id}&course_id=faked&student=faked&timestamp=faked&checksum=faked"

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."  # noqa: E501 W503
    )


@pytest.mark.gen_test
def test_feedback_post_authenticated_no_student(app, clear_database):  # noqa: F811
    assignment_id = "my_assignment"
    url = f"/feedback?assignment_id={assignment_id}&course_id=faked&notebook=faked&timestamp=faked&checksum=faked"

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."  # noqa: E501 W503
    )


@pytest.mark.gen_test
def test_feedback_post_authenticated_no_timestamp(app, clear_database):  # noqa: F811
    assignment_id = "my_assignment"
    url = f"/feedback?assignment_id={assignment_id}&course_id=faked&notebook=faked&student=faked&checksum=faked"

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."  # noqa: E501 W503
    )


@pytest.mark.gen_test
def test_feedback_post_authenticated_no_checksum(app, clear_database):  # noqa: F811
    assignment_id = "my_assignment"
    url = f"/feedback?assignment_id={assignment_id}&course_id=faked&notebook=faked&student=faked&timestamp=faked"

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."  # noqa: E501 W503
    )


@pytest.mark.gen_test
def test_feedback_post_authenticated_with_params(app, clear_database):  # noqa: F811
    assignment_id = "my_assignment"

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id=course_2"
        f"&notebook=faked"
        f"&student=faked"
        f"&timestamp=faked"
        f"&checksum=faked"
    )

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    assert r.status_code == 404


@pytest.mark.gen_test
def test_feedback_post_authenticated_with_incorrect_assignment_id(app, clear_database):  # noqa: F811
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )
    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=released_files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + f"/submission?course_id={course_id}&assignment_id={assignment_id}&timestamp={timestamp}",
            files=released_files,
        )

    url = (
        f"/feedback?assignment_id=faked"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    assert r.status_code == 404
    shutil.rmtree(app.base_storage_location)


@pytest.mark.gen_test
def test_feedback_post_authenticated_with_incorrect_notebook_id(app, clear_database):  # noqa: F811
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )

    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=released_files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + f"/submission?course_id={course_id}&assignment_id={assignment_id}&timestamp={timestamp}",
            files=released_files,
        )

    url = (
        f"/feedback?assignment_id={course_id}"
        f"&course_id={course_id}"
        f"&notebook=faked"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    assert r.status_code == 404
    shutil.rmtree(app.base_storage_location)


@pytest.mark.gen_test
def test_feedback_post_authenticated_with_incorrect_student_id(app, clear_database):  # noqa: F811
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_brobbere_student
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )

    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=released_files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + f"/submission?course_id={course_id}&assignment_id={assignment_id}&timestamp={timestamp}",
            files=released_files,
        )

    url = (
        f"/feedback?assignment_id={course_id}"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    assert r.status_code == 404
    shutil.rmtree(app.base_storage_location)


# Not yet implemented on exchange server...
@pytest.mark.skip
@pytest.mark.gen_test
def test_feedback_post_authenticated_with_incorrect_checksum(app, clear_database):  # noqa: F811
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.now(tz).strftime(timestamp_format)
    notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )

    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=released_files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + f"/submission?course_id={course_id}&assignment_id={assignment_id}&timestamp={timestamp}",
            files=released_files,
        )

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum=faked"
    )

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    assert r.status_code == 403
    shutil.rmtree(app.base_storage_location)


@pytest.mark.gen_test
def test_feedback_post_authenticated_with_correct_params(app, clear_database):  # noqa: F811
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )

    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=released_files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + f"/submission?course_id={course_id}&assignment_id={assignment_id}&timestamp={timestamp}",
            files=released_files,
        )

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    shutil.rmtree(app.base_storage_location)


@pytest.mark.gen_test
def test_feedback_post_authenticated_with_correct_params_incorrect_instructor(app, clear_database):  # noqa: F811
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )

    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=released_files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + f"/submission?course_id={course_id}&assignment_id={assignment_id}&timestamp={timestamp}",
            files=released_files,
        )

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )

    with patch.object(BaseHandler, "get_current_user", return_value=user_lkihlman_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == f"User not subscribed to course {course_id}"
    shutil.rmtree(app.base_storage_location)


@pytest.mark.gen_test
def test_feedback_post_authenticated_with_correct_params_student_submitter(app, clear_database):  # noqa: F811
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )

    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=released_files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + f"/submission?course_id={course_id}&assignment_id={assignment_id}&timestamp={timestamp}",
            files=released_files,
        )

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == f"User not an instructor to course {course_id}"
    shutil.rmtree(app.base_storage_location)


@pytest.mark.gen_test
def test_feedback_get_authenticated_with_incorrect_student(app, clear_database):  # noqa: F811
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )

    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=released_files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + f"/submission?course_id={course_id}&assignment_id={assignment_id}&timestamp={timestamp}",
            files=released_files,
        )

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    url = f"/feedback?assignment_id={assignment_id}&course_id={course_id}"

    with patch.object(BaseHandler, "get_current_user", return_value=user_brobbere_student):
        r = yield async_requests.get(app.url + url)

    assert r.status_code == 200

    response_data = r.json()
    assert response_data["success"] is True
    assert len(response_data["feedback"]) == 0
    shutil.rmtree(app.base_storage_location)


@pytest.mark.gen_test
def test_feedback_get_authenticated_with_correct_params(app, clear_database):  # noqa: F811
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )

    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=released_files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + f"/submission?course_id={course_id}&assignment_id={assignment_id}&timestamp={timestamp}",
            files=released_files,
        )

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    url = f"/feedback?assignment_id={assignment_id}&course_id={course_id}"

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + url)

    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert len(response_data["feedback"]) >= 1
    assert response_data["feedback"][0].get("content") == feedback_base64.decode("utf-8")
    shutil.rmtree(app.base_storage_location)


@pytest.mark.gen_test
def test_feedback_get_broken_nbex_user(app, clear_database, caplog):  # noqa: F811
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )

    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=released_files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + f"/submission?course_id={course_id}&assignment_id={assignment_id}&timestamp={timestamp}",
            files=released_files,
        )

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    url = f"/feedback?assignment_id={assignment_id}&course_id={course_id}"

    # finally able to do the test.
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz):
        r = yield async_requests.get(app.url + url)

    assert r.status_code == 500
    assert "Both current_course ('None') and current_role ('None') must have values. User was '1-kiz'" in caplog.text
    shutil.rmtree(app.base_storage_location)


# test feedback picks up the correct assignment when two courses have the same assignment name
# Should pick up course 2.
@pytest.mark.gen_test
def test_feedback_get_correct_assignment_across_courses(app, clear_database):  # noqa: F811
    pass
    # set up the situation
    assignment_id = "assign_a"
    course_1 = "course_1"
    course_2 = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.now(tz).strftime(timestamp_format)
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_2, assignment_id, notebook, student["name"], timestamp),
    )
    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}

    # release assignment on course 1 & 2
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + f"/assignment?course_id={course_1}&assignment_id={assignment_id}",
            files=released_files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + f"/assignment?course_id={course_2}&assignment_id={assignment_id}",
            files=released_files,
            **kwargs,
        )

    # Now fetch & submit on course 2 as student
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + f"/assignment?course_id={course_2}&assignment_id={assignment_id}")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + f"/submission?course_id={course_2}&assignment_id={assignment_id}&timestamp={timestamp}",
            files=released_files,
        )

    # Instructor releases for course 2
    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id={course_2}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    url = f"/feedback?assignment_id={assignment_id}&course_id={course_1}"

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + url)

    assert r.status_code == 404

    url = f"/feedback?assignment_id={assignment_id}&course_id={course_2}"

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + url)

    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert len(response_data["feedback"]) >= 1
    assert response_data["feedback"][0].get("content") == feedback_base64.decode("utf-8")
    shutil.rmtree(app.base_storage_location)
