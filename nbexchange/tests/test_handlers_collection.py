import logging
import os
import pathlib
import re
import shutil

import pytest
from mock import patch

from nbexchange.handlers.base import BaseHandler
from nbexchange.tests.utils import (  # noqa: F401 "clear_database"
    async_requests,
    clear_database,
    get_files_dict,
    user_brobbere_student,
    user_kiz,
    user_kiz_instructor,
    user_kiz_student,
)

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)

# set up the file to be uploaded as part of the testing later
release_files, notebooks, timestamp = get_files_dict()


# #### POST /collection #### #


# No method available (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_collection_is_501(app):
    r = yield async_requests.post(app.url + "/collection")
    assert r.status_code == 501


# subscribed user makes no difference (501, because we've hard-coded it)
@pytest.mark.gen_test
def test_post_collection_is_501_even_authenticaated(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(app.url + "/collection?course_id=course_2")
    assert r.status_code == 501


# #### GET /collection (download/collect student submissions) #### #

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


# require authenticated user
@pytest.mark.gen_test
def test_get_collection_requires_authentication(app, clear_database):  # noqa: F811
    r = yield async_requests.get(app.url + "/collection")
    assert r.status_code == 403


# Requires three params (none)
@pytest.mark.gen_test
def test_get_collection_requires_parameters(app):
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/collection")
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Collection call requires a course code, an assignment code, and a path"


# Requires three params (given course & assignment)
# (needs to be submitted before it can listed for collection )
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_get_collection_catches_missing_path(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )
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
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Collection call requires a course code, an assignment code, and a path"
    shutil.rmtree(app.base_storage_location)


# Requires three params (given course & path)
# (needs to be submitted before it can listed for collection )
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_get_collection_catches_missing_assignment(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  # Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        r = yield async_requests.get(
            app.url + f"/collection?course_id={collected_data['course_id']}&path={collected_data['path']}"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Collection call requires a course code, an assignment code, and a path"
    shutil.rmtree(app.base_storage_location)


# Requires three params (given assignment & path)
# (needs to be submitted before it can listed for collection )
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_get_collection_catches_missing_course(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  # Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        r = yield async_requests.get(
            app.url + f"/collection?path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "Collection call requires a course code, an assignment code, and a path"
    shutil.rmtree(app.base_storage_location)


# Has all three params, not subscribed to course
# (needs to be submitted before it can listed for collection )
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_get_collection_checks_for_user_subscription(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  # Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        params = f"/collection?course_id=course_1&path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"  # noqa: E501
        r = yield async_requests.get(
            app.url + params,
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "User not subscribed to course course_1"
    shutil.rmtree(app.base_storage_location)


# Has all three params, student can't collect (note this is hard-coded params, as students can
#   list items available for collection)
# (needs to be released to register the assignment )
@pytest.mark.gen_test
def test_get_collection_check_catches_student_role(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_brobbere_student):
        r = yield async_requests.get(
            app.url + "/collection?course_id=course_2&path=/foo/car/file.gz&assignment_id=assign_a"
        )
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["success"] is False
    assert response_data["note"] == "User not an instructor to course course_2"
    shutil.rmtree(app.base_storage_location)


# Has all three params, instructor can collect
# (needs to be submitted before it can listed for collection )
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_get_collection_confirm_instructor_does_download(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  # Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        params = f"/collection?course_id={collected_data['course_id']}&path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"  # noqa: E501 W503
        r = yield async_requests.get(app.url + params)
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "application/gzip"
    assert int(r.headers["Content-Length"]) > 0
    shutil.rmtree(app.base_storage_location)


# broken nbex_user throws a 500 error on the server
# (needs to be submitted before it can listed for collection )
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_get_collection_broken_nbex_user(app, clear_database, caplog):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  # Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        with patch.object(BaseHandler, "get_current_user", return_value=user_kiz):
            params = f"/collection?course_id={collected_data['course_id']}&path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"  # noqa: E501
            r = yield async_requests.get(app.url + params)
    assert r.status_code == 500
    assert "Both current_course ('None') and current_role ('None') must have values. User was '1-kiz'" in caplog.text
    shutil.rmtree(app.base_storage_location)


# Confirm that multiple submissions are listed
@pytest.mark.gen_test
async def test_collection_actions_show_correctly(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = await async_requests.post(  # release
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
        r = await async_requests.get(app.url + "/assignment?&course_id=course_2&assignment_id=assign_a")  # fetch
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = await async_requests.post(  # submit
            app.url + params,
            files=release_files,
        )
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A01.0%20UTC"
        r = await async_requests.post(  # submit
            app.url + params,
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_brobbere_student):
        r = yield async_requests.get(
            app.url + "/assignment?&course_id=course_2&assignment_id=assign_a"
        )  # fetch as another user
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )  # submit as that user
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A01.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )  # submit as that user again
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.get(app.url + "/collections?course_id=course_2&assignment_id=assign_a")
        # The 'collections' call returns only submissions, but all for that assignment
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["success"] is True
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
            params = f"/collection?course_id={collected_data['course_id']}&path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"  # noqa: E501
            r = yield async_requests.get(app.url + params)  # collect submission

        r = yield async_requests.get(app.url + "/assignments?course_id=course_2")

        # The 'assignments' call returns only the actions for the specific user
        # So this instructor has submitted twice, but collected 4 times
        assert r.status_code == 200
        response_data = r.json()
        assert response_data["success"] is True
        assert "note" not in response_data  # just that it's missing
        paths = list(map(lambda assignment: assignment["path"], response_data["value"]))
        actions = list(map(lambda assignment: assignment["status"], response_data["value"]))

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
    with patch.object(BaseHandler, "get_current_user", return_value=user_brobbere_student):
        r = yield async_requests.get(app.url + "/assignments?course_id=course_2")
        response_data = r.json()
        actions = list(map(lambda assignment: assignment["status"], response_data["value"]))

        assert len(actions) == 4
        assert actions == ["released", "fetched", "submitted", "submitted"]
    shutil.rmtree(app.base_storage_location)


# what happens the path doesn't match
# (needs to be submitted before it can listed for collection )
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_get_collection_path_is_incorrect(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  # Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        params = f"/collection?course_id={collected_data['course_id']}&path=/some/random/path&assignment_id={collected_data['assignment_id']}"  # noqa: E501
        r = yield async_requests.get(app.url + params)
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "application/gzip"
    assert int(r.headers["Content-Length"]) == 0
    shutil.rmtree(app.base_storage_location)


# what happens when collections returns a fetched_feedback with an empty path
# (needs to be submitted before it can listed for collection )
# (needs to be fetched before it can be submitted )
# (needs to be released before it can be fetched )
@pytest.mark.gen_test
def test_get_collection_with_a_blank_feedback_path_injected(app, clear_database):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )

    # Now manually inject a `feedback_fetched` action
    import nbexchange.models.actions
    from nbexchange.database import scoped_session

    with scoped_session() as session:
        action = nbexchange.models.actions.Action(
            user_id=3,
            assignment_id="assign_a",
            action="feedback_fetched",
            location=None,
        )
        session.add(action)

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  # Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        params = f"/collection?course_id={collected_data['course_id']}&path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"  # noqa: E501
        r = yield async_requests.get(
            app.url + params,
        )
    assert r.status_code == 200
    assert r.headers["Content-Type"] == "application/gzip"
    assert int(r.headers["Content-Length"]) > 0
    shutil.rmtree(app.base_storage_location)


# File present, but not readable
# lets submit a file, then nobble it on the server, before trying to fetch it
@pytest.mark.gen_test
def test_get_collection_unable_to_read_file(app, clear_database, caplog):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )
    # make the file non-readable, so the fetch fails to open it
    exchange_path = app.base_storage_location

    files = list(pathlib.Path(exchange_path).rglob("*"))
    print(f"chmodding {files[-1]}")
    os.chmod(files[-1], 0o333)
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  # Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        params = f"/collection?course_id={collected_data['course_id']}&path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"  # noqa: E501
        r = yield async_requests.get(
            app.url + params,
        )
    assert r.status_code == 500
    assert "collection handler unable to open" in caplog.text
    assert False
    # shutil.rmtree(app.base_storage_location)


# File somehow missing
# lets release a file, then nobble it on the server, before trying to fetch it
@pytest.mark.gen_test
def test_get_collection_unable_to_read_file(app, clear_database, caplog):  # noqa: F811
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        r = yield async_requests.post(
            app.url + "/assignment?course_id=course_2&assignment_id=assign_a",
            files=release_files,
        )
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        r = yield async_requests.get(app.url + "/assignment?course_id=course_2&assignment_id=assign_a")
    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_student):
        params = "/submission?course_id=course_2&assignment_id=assign_a&timestamp=2020-01-01%2000%3A00%3A00.0%20UTC"
        r = yield async_requests.post(
            app.url + params,
            files=release_files,
        )

    # Now move the file to a different location, so the fetch fails to open it
    shutil.move(f"{app.base_storage_location}/1/", f"{app.base_storage_location}/2/")

    with patch.object(BaseHandler, "get_current_user", return_value=user_kiz_instructor):
        collected_data = None
        r = yield async_requests.get(
            app.url + "/collections?course_id=course_2&assignment_id=assign_a"
        )  # Get the data we need to make test the call we want to make
        response_data = r.json()
        collected_data = response_data["value"][0]
        params = f"/collection?course_id={collected_data['course_id']}&path={collected_data['path']}&assignment_id={collected_data['assignment_id']}"  # noqa: E501
        r = yield async_requests.get(
            app.url + params,
        )
    assert r.status_code == 500
    assert "No such file or directory:" in caplog.text
    shutil.rmtree(app.base_storage_location)
