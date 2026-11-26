"""Read grade metadata from the exact HTML bytes submitted for release."""

import base64
import binascii
import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal, DecimalException

ARTIFACT_SUFFIX = re.compile(rb"\n<!-- noteable-feedback-v1:([A-Za-z0-9+/=]+) -->\n?\Z")


def read_feedback_revision(body, *, course, assignment, learner, notebook, timestamp, notebooks):
    marker = ARTIFACT_SUFFIX.search(body)
    if marker is None:
        return None, None
    try:
        artifact = json.loads(base64.b64decode(marker[1], validate=True))
        release = artifact["release"]
        if (
            artifact["html_sha256"] != hashlib.sha256(body[: marker.start()]).hexdigest()
            or artifact["notebook"] != notebook
            or release["course_code"] != course
            or release["assignment_code"] != assignment
            or release["learner_name"] != learner
            or datetime.fromisoformat(release["submission_timestamp"]) != timestamp
            or not isinstance(release["notebooks"], dict)
            or release["notebooks"].keys() != notebooks
        ):
            return None, None

        state, grade = release["grade_state"], release["grade"]
        if state == "ready":
            assignment_id = grade["assignment_id"]
            amounts = [Decimal(grade[key]) for key in ("score_given", "score_maximum")]
            if (
                not isinstance(assignment_id, str)
                or not assignment_id.strip()
                or len(assignment_id) > 256
                or not all(amount.is_finite() and 0 <= amount < 10000000 for amount in amounts)
            ):
                return None, None
        elif state != "ungraded" or grade is not None:
            return None, None
        revision = hashlib.sha256(json.dumps(release, allow_nan=False, sort_keys=True).encode()).hexdigest()
    except (binascii.Error, DecimalException, ValueError, KeyError, TypeError):
        return None, None

    return revision, release
