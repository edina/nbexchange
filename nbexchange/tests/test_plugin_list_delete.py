import logging

import pytest
from mock import patch
from nbgrader.coursedir import CourseDirectory

from nbexchange.plugin import Exchange, ExchangeList

logger = logging.getLogger(__file__)
logger.setLevel(logging.ERROR)


@pytest.mark.gen_test
def test_list_delete(plugin_config, tmpdir):
    plugin_config.CourseDirectory.course_id = "no_course"
    plugin_config.CourseDirectory.assignment_id = "assign_1_1"
    plugin_config.ExchangeList.remove = True

    plugin = ExchangeList(coursedir=CourseDirectory(config=plugin_config), config=plugin_config)

    def api_request(*args, **kwargs):
        assert args[0] == ("assignment?course_id=no_course&assignment_id=assign_1_1")
        assert "method" not in kwargs or kwargs.get("method").lower() == "delete"
        return type("Request", (object,), {"status_code": 200})

    with patch.object(Exchange, "api_request", side_effect=api_request):
        plugin.start()
