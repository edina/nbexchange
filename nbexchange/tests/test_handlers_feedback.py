import datetime
import sys
import base64

import pytest
from mock import patch

from nbexchange.handlers.base import BaseHandler
from nbexchange.tests.utils import (
    async_requests,
    AsyncSession,
    get_feedback_dict,
    get_files_dict,
    user_brobbere_student,
    user_kiz_instructor,
    user_kiz_student,
    user_lkihlman_instructor,
)
from nbgrader.utils import notebook_hash, make_unique_key


def submit_assignment(app, course, assignment, uploads, notebooks=None):
    kwargs = {}
    if notebooks is not None:
        kwargs = {"data": {"notebooks": notebooks}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + f"/assignment?course_id={course}&assignment_id={assignment}",
            files=uploads,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + f"/assignment?course_id={course}&assignment_id={assignment}"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + f"/submission?course_id={course}&assignment_id={assignment}",
            files=uploads,
        )


# set up the file to be uploaded
feedback_filename = sys.argv[0]  # ourself :)
feedbacks = get_feedback_dict(feedback_filename)
feedback_base64 = base64.b64encode(open(sys.argv[0]).read().encode("utf-8"))
files = get_files_dict(sys.argv[0])  # ourself :)


@pytest.mark.gen_test
def test_feedback_unauthenticated(app):
    """
    Require authenticated user
    """
    r = yield async_requests.get(app.url + "/feedback")
    assert r.status_code == 403


@pytest.mark.gen_test
def test_feedback_authenticated_no_params(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/feedback")
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "Feedback call requires an assignment id."


@pytest.mark.gen_test
def test_feedback_authenticated_with_params(app):
    assignment_id = "my_assignment"

    url = f"/feedback?assignment_id={assignment_id}"

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + url)

    assert r.status_code == 404


@pytest.mark.gen_test
def test_feedback_post_unauthenticated(app):
    """
    Require authenticated user for posting
    """
    r = yield async_requests.post(app.url + "/feedback", files=feedbacks)
    assert r.status_code == 403


@pytest.mark.gen_test
def test_feedback_post_authenticated_no_params(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + "/feedback", files=feedbacks)
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."
    )


@pytest.mark.gen_test
def test_feedback_post_authenticated_no_assignment_id(app):
    url = f"/feedback?course_id=faked&notebook=faked&student=faked&timestamp=faked&checksum=faked"

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."
    )


@pytest.mark.gen_test
def test_feedback_post_authenticated_no_course_id(app):
    assignment_id = "my_assignment"
    url = f"/feedback?assignment_id={assignment_id}&notebook=faked&student=faked&timestamp=faked&checksum=faked"

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."
    )


@pytest.mark.gen_test
def test_feedback_post_authenticated_no_notebook(app):
    assignment_id = "my_assignment"
    url = f"/feedback?assignment_id={assignment_id}&course_id=faked&student=faked&timestamp=faked&checksum=faked"

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."
    )


@pytest.mark.gen_test
def test_feedback_post_authenticated_no_student(app):
    assignment_id = "my_assignment"
    url = f"/feedback?assignment_id={assignment_id}&course_id=faked&notebook=faked&timestamp=faked&checksum=faked"

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."
    )


@pytest.mark.gen_test
def test_feedback_post_authenticated_no_timestamp(app):
    assignment_id = "my_assignment"
    url = f"/feedback?assignment_id={assignment_id}&course_id=faked&notebook=faked&student=faked&checksum=faked"

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."
    )


@pytest.mark.gen_test
def test_feedback_post_authenticated_no_checksum(app):
    assignment_id = "my_assignment"
    url = f"/feedback?assignment_id={assignment_id}&course_id=faked&notebook=faked&student=faked&timestamp=faked"

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    response_data = r.json()
    assert response_data["success"] is False
    assert (
        response_data["note"]
        == "Feedback call requires a course id, assignment id, notebook name, student id, checksum and timestamp."
    )


@pytest.mark.gen_test
def test_feedback_post_authenticated_with_params(app):
    assignment_id = "my_assignment"

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id=course_2"
        f"&notebook=faked"
        f"&student=faked"
        f"&timestamp=faked"
        f"&checksum=faked"
    )

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    assert r.status_code == 404


@pytest.mark.gen_test
def test_feedback_post_authenticated_with_incorrect_assignment_id(app):
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.datetime.utcnow().isoformat()
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )
    # submit_assignment(app, course_id, assignment_id, files, notebooks=[notebook])
    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
        )

    url = (
        f"/feedback?assignment_id=faked"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    assert r.status_code == 404


@pytest.mark.gen_test
def test_feedback_post_authenticated_with_incorrect_notebook_id(app):
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.datetime.utcnow().isoformat()
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )
    # submit_assignment(app, course_id, assignment_id, files, notebooks=[notebook])
    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
        )

    url = (
        f"/feedback?assignment_id={course_id}"
        f"&course_id={course_id}"
        f"&notebook=faked"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    assert r.status_code == 404


@pytest.mark.gen_test
def test_feedback_post_authenticated_with_incorrect_student_id(app):
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_brobbere_student
    timestamp = datetime.datetime.utcnow().isoformat()
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )
    # submit_assignment(app, course_id, assignment_id, files, notebooks=[notebook])
    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
        )

    url = (
        f"/feedback?assignment_id={course_id}"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    assert r.status_code == 404


# Not yet implemented on exchange server...
@pytest.mark.skip
def test_feedback_post_authenticated_with_incorrect_checksum(app):
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.datetime.utcnow().isoformat()
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )
    # submit_assignment(app, course_id, assignment_id, files, notebooks=[notebook])
    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
        )

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum=faked"
    )

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    assert r.status_code == 403


@pytest.mark.gen_test
def test_feedback_post_authenticated_with_correct_params(app):
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.datetime.utcnow().isoformat()
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )
    # submit_assignment(app, course_id, assignment_id, files, notebooks=[notebook])
    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
        )

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True


@pytest.mark.gen_test
def test_feedback_post_authenticated_with_correct_params_incorrect_instructor(app):
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.datetime.utcnow().isoformat()
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )
    # submit_assignment(app, course_id, assignment_id, files, notebooks=[notebook])
    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
        )

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_lkihlman_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == f"User not subscribed to course {course_id}"


@pytest.mark.gen_test
def test_feedback_post_authenticated_with_correct_params_student_submitter(app):
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.datetime.utcnow().isoformat()
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )
    # submit_assignment(app, course_id, assignment_id, files, notebooks=[notebook])
    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
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


@pytest.mark.gen_test
def test_feedback_get_authenticated_with_incorrect_student(app):
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.datetime.utcnow().isoformat()
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )
    # submit_assignment(app, course_id, assignment_id, files, notebooks=[notebook])
    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
        )

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    url = f"/feedback?assignment_id={assignment_id}"

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.get(app.url + url)

    assert r.status_code == 200

    response_data = r.json()
    assert response_data["success"] is True
    assert len(response_data["feedback"]) == 0


@pytest.mark.gen_test
def test_feedback_get_authenticated_with_correct_params(app):
    assignment_id = "assign_a"
    course_id = "course_2"
    notebook = "notebook"
    student = user_kiz_student
    timestamp = datetime.datetime.utcnow().isoformat()
    checksum = notebook_hash(
        feedback_filename,
        make_unique_key(course_id, assignment_id, notebook, student["name"], timestamp),
    )
    # submit_assignment(app, course_id, assignment_id, files, notebooks=[notebook])
    # XXX: Doing this in a separate function doesn't work for some reason (Exchange doesn't get called)
    kwargs = {"data": {"notebooks": [notebook]}}
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url
            + f"/assignment?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
            **kwargs,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + f"/assignment?course_id={course_id}&assignment_id={assignment_id}"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url
            + f"/submission?course_id={course_id}&assignment_id={assignment_id}",
            files=files,
        )

    url = (
        f"/feedback?assignment_id={assignment_id}"
        f"&course_id={course_id}"
        f"&notebook={notebook}"
        f"&student={student['name']}"
        f"&timestamp={timestamp}"
        f"&checksum={checksum}"
    )
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + url, files=feedbacks)

    url = f"/feedback?assignment_id={assignment_id}"

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + url)

    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is True
    assert len(response_data["feedback"]) >= 1
    assert response_data["feedback"][0].get("content") == feedback_base64.decode(
        "utf-8"
    )
