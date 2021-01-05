import logging
import pytest
import re
import sys

from mock import patch
from nbexchange.handlers.base import BaseHandler
from nbexchange.tests.utils import (
    async_requests,
    get_files_dict,
    user_kiz_instructor,
    user_kiz_student,
    user_brobbere_student,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

# set up the file to be uploaded as part of the testing later
files = get_files_dict(sys.argv[0])  # ourself :)

##### POST /collection #####

# No method available (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_collection0(app):
    r = yield async_requests.post(app.url + "/collection")
    assert r.status_code == 501


# subscribed user makes no difference (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_assignments1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(app.url + "/collection?course_id=course_2")
    assert r.status_code == 501


##### GET /collection (download/collect student submissions) #####

# require authenticated user
@pytest.mark.gen_test
def test_collection0(app):
    r = yield async_requests.get(app.url + "/collection")
    assert r.status_code == 403


# Requires three params (none)
@pytest.mark.gen_test
def test_collection1(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + "/collection")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Collection call requires a course code, an assignment code, and a path"
    )


# Requires three params (given course & assignment)
# (needs to be submitted before it can listed for collection )
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_collection2(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  ## Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        r = yield async_requests.get(
            app.url
            + f"/collection?course_id={collected_data['course_id']}&assignment_id={collected_data['assignment_id']}"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Collection call requires a course code, an assignment code, and a path"
    )


# Requires three params (given course & path)
# (needs to be submitted before it can listed for collection )
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_collection3(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  ## Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        r = yield async_requests.get(
            app.url
            + f"/collection?course_id={collected_data['course_id']}&path={collected_data['path']}"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Collection call requires a course code, an assignment code, and a path"
    )


# Requires three params (given assignment & path)
# (needs to be submitted before it can listed for collection )
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_collection4(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  ## Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        r = yield async_requests.get(
            app.url
            + f"/collection?path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert (
        response_data["note"]
        == "Collection call requires a course code, an assignment code, and a path"
    )


# Has all three params, not subscribed to course
# (needs to be submitted before it can listed for collection )
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_collection5(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  ## Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        r = yield async_requests.get(
            app.url
            + f"/collection?course_id=course_1&path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == "User not subscribed to course course_1"


# Has all three params, student can't collect (note this is hard-coded params, as students can list items available for collection)
# (needs to be released to register the assignment )
@pytest.mark.gen_test
def test_collection6(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.get(
            app.url
            + f"/collection?course_id=course_2&path=/foo/car/file.gz&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] == False
    assert response_data["note"] == f"User not an instructor to course course_2"


# Has all three params, instructor can collect
# (needs to be submitted before it can listed for collection )
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_collection7(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a"
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  ## Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        r = yield async_requests.get(
            app.url
            + f"/collection?course_id={collected_data['course_id']}&path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"
        )
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "application/gzip"
    assert int(r.headers["Content-Length"]) > 0


# Confirm that multiple submissions are listed
@pytest.mark.gen_test
async def test_post_assignment9(app):
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = await async_requests.post(  # release
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
        r = await async_requests.get(  # fetch
            app.url + "/assignment?&course_id=course_2&assignment_id=assign_a"
        )
        r = await async_requests.post(  # submit
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
        r = await async_requests.post(  # submit
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=files,
        )
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.get(
            app.url + "/assignment?&course_id=course_2&assignment_id=assign_a"
        )  # fetch as another user
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=files,
        )  # submit as that user
        r = yield async_requests.post(
            app.url + "/submission?course_id=course_2&assignment_id=assign_a",
            files=files,
        )  # submit as that user again
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )
        # The 'collections' call returns only submissions, but all for that assignment
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["success"] == True
        assert "note" not in response_data  # just that it's missing
        paths = list(map(lambda assignment: assignment["path"], response_data["value"]))

        assert len(paths) == 4  # the collections call only returns submitted items
        # path in submission contains org + course + assignment + user
        assert re.search("1/submitted/course_2/assign_a/1-kiz", paths[0])
        assert re.search("1/submitted/course_2/assign_a/1-kiz", paths[1])
        assert re.search("1/submitted/course_2/assign_a/1-brobbere", paths[2])
        assert re.search("1/submitted/course_2/assign_a/1-brobbere", paths[3])

        collected_items = response_data["value"]
        for collected_data in collected_items:
            r = yield async_requests.get(  # collect submission
                app.url
                + f"/collection?course_id={collected_data['course_id']}&path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"
            )

        r = yield async_requests.get(app.url + "/assignments?course_id=course_2")

        # The 'assignments' call returns only the actions for the specific user
        # So this instructor has submitted twice, but collected 4 times
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["success"] == True
        assert "note" not in response_data  # just that it's missing
        paths = list(map(lambda assignment: assignment["path"], response_data["value"]))
        actions = list(
            map(lambda assignment: assignment["status"], response_data["value"])
        )

        assert len(paths) == 8
        assert actions == [
            "released",
            "fetched",
            "submitted",
            "submitted",
            "collected",
            "collected",
            "collected",
            "collected",
        ]
        assert paths[2] == paths[4]  # 1st submit = 1st collect
        assert paths[3] == paths[5]  # 2nd submit = 2nd collect

    # As a different user, we get a different return
    with patch.object(
        BaseHandler, "get_current_user", return_value=user_brobbere_student
    ):
        r = yield async_requests.get(app.url + "/assignments?course_id=course_2")
        response_data = r.json()
        actions = list(
            map(lambda assignment: assignment["status"], response_data["value"])
        )

        assert len(actions) == 4
        assert actions == ["released", "fetched", "submitted", "submitted"]
