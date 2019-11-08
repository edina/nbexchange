import pytest
from mock import patch

from nbexchange.handlers.base import BaseHandler
from nbexchange.tests.utils import async_requests, user_kiz_instructor


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
    assert (
        response_data["note"]
        == "Feedback call requires a notebook id."
    )

@pytest.mark.gen_test
def test_feedback_authenticated_with_params(app):
    notebook_id = 'my_notebook'

    url = f"/feedback?notebook_id={notebook_id}"

    with patch.object(
        BaseHandler, "get_current_user", return_value=user_kiz_instructor
    ):
        r = yield async_requests.get(app.url + url)

    assert r.status_code == 404



