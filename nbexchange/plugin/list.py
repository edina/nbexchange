import glob
import json
import os
import sys

import nbgrader.exchange.abc as abc
from .exchange import Exchange
from traitlets import Bool, Unicode
from urllib.parse import quote_plus


# "outbound" is files released by instructors (.... but there may be local copies!)
# "inbound" is files submitted by students (on external service)
# "cached" is files submitted by students & collected by instructors (so on local disk)
class ExchangeList(abc.ExchangeList, Exchange):
    def do_copy(self, src, dest):
        pass

    fetched_root = Unicode("", help="Root location for files to be fetched into")

    # the list of assignments the exchange knows about
    assignments = []

    # for filtering on-disk items from exchange items
    # (eg removed 'released' items if the 'fetched' item is on disk)
    seen_assignments = {"fetched": [], "collected": []}

    def query_exchange(self):
        if self.course_id:
            """List assignments for specific course"""
            r = self.api_request(f"assignments?course_id={quote_plus(self.course_id)}")
        else:
            """List assignments for all courses"""
            r = self.api_request(f"assignments")

        self.log.debug(f"Got back {r} when listing assignments")

        try:
            assignments = r.json()
        except json.decoder.JSONDecodeError:
            self.log.error(f"Got back an invalid response when listing assignments")
            return []

        self.log.info(
            f"ExchangeList.query_exchange - Got back {assignments} when listing assignments"
        )

        return assignments["value"]

    def init_src(self):
        pass

    # sets self.assignments to be the list of assignment records that match the
    #  released/submitted/cached criteria configured
    def init_dest(self):
        course_id = self.course_id if self.course_id else "*"
        assignment_id = (
            self.coursedir.assignment_id if self.coursedir.assignment_id else "*"
        )
        student_id = self.coursedir.student_id if self.coursedir.student_id else "*"

        self.assignments = []

        local_assignments = self.query_exchange()
        self.log.debug(f"ExternalExchange.list.init_dest collected {local_assignments}")

        # if "inbound", looking for inbound (submitted) records
        # elif 'cached', looking for already downloaded files
        # else, looking for outbound (released) files
        if self.inbound or self.cached:
            for assignment in local_assignments:
                if assignment.get("status") == "submitted":
                    self.assignments.append(assignment)
        else:
            self.assignments = local_assignments

    def copy_files(self):
        pass

    ### We need to add feedback into submitted items
    ### (this may not be the best place to process them)
    def parse_assignment(self, assignment):
        # For fetched & collected items - we want to know what the user has on-disk
        # rather than what the exchange server things we have.
        if assignment.get("status") in ("fetched", "collected"):
            assignment_directory = (
                self.fetched_root + "/" + assignment.get("assignment_id")
            )
            assignment["notebooks"] = []
            # Find the ipynb files
            for notebook in sorted(
                glob.glob(os.path.join(assignment_directory, "*.ipynb"))
            ):
                notebook_id = os.path.splitext(os.path.split(notebook)[1])[0]
                assignment["notebooks"].append(
                    {
                        "path": notebook,
                        "notebook_id": notebook_id,
                        "has_local_feedback": False,
                        "has_exchange_feedback": False,
                        "local_feedback_path": None,
                        "feedback_updated": False,
                    }
                )

            if len(assignment["notebooks"]):
                self.seen_assignments[assignment.get("status")].append(
                    assignment["assignment_id"]
                )
                return assignment

        else:
            return assignment

    ### Need to add feedback into here!!!
    ### (check what the 'exchange.parse_assignment(path)' puts into 'info[]')
    ### Needs 'notebook' ling moved to 'action'
    def parse_assignments(self):
        # self.assignments = self.query_exchange()  # This should really set by init_dest

        # We want to check the local disk for "fetched" items, not what the external server
        # says we should have
        interim_assignments = []
        for assignment in self.assignments:
            interim_assignments.append(self.parse_assignment(assignment))
            self.log.info(
                f"parse_assignment singular assignment returned: {assignment}"
            )

        # now we build three sub-lists:
        # - one "fetched" per assignment_id
        # - the last "released" per assignment_id - but only if they've not been "fetched"
        # - all "collected"
        # - all "submitted"
        held_assignments = {"fetched": {}, "released": {}}
        my_assignments = []
        for assignment in interim_assignments:
            # Skip those not being seen
            if assignment is None:
                continue

            assignment_directory = (
                self.fetched_root + "/" + assignment.get("assignment_id")
            )

            # Only keep a fetched assignment directory is on disk.
            # Keep only one fetched per assignment_id - any will do
            if assignment.get("status") == "fetched" and os.path.isdir(
                assignment_directory
            ):
                held_assignments["fetched"][
                    assignment.get("assignment_id")
                ] = assignment
                continue

            # filter out all the released items:
            if assignment.get("status") == "released":
                # This is complicated:
                #  - If the user has "fetched" the assignment, and the asignment directory is on disk
                #    ... don't keep it
                #  - otherwise keep the latest one
                if assignment.get("assignment_id") in self.seen_assignments[
                    "fetched"
                ] and os.path.isdir(assignment_directory):
                    continue
                else:
                    latest = held_assignments["released"].get(
                        assignment.get("assignment_id"),
                        {"timestamp": "1990-01-01 00:00:00"},
                    )
                    if assignment.get("timestamp") > latest.get("timestamp"):
                        held_assignments["released"][
                            assignment.get("assignment_id")
                        ] = assignment
                    continue

            # "Submitted" assignments [may] have feedback
            if assignment.get("status") == "released":
                if assignment["notebooks"]:
                    has_local_feedback = all(
                        [nb["has_local_feedback"] for nb in assignment["notebooks"]]
                    )
                    has_exchange_feedback = all(
                        [nb["has_exchange_feedback"] for nb in assignment["notebooks"]]
                    )
                    feedback_updated = any(
                        [nb["feedback_updated"] for nb in assignment["notebooks"]]
                    )
                else:
                    has_local_feedback = False
                    has_exchange_feedback = False
                    feedback_updated = False

                assignment["has_local_feedback"] = has_local_feedback
                assignment["has_exchange_feedback"] = has_exchange_feedback
                assignment["feedback_updated"] = feedback_updated
                assignment["local_feedback_path"] = None

                # We keep everything we've not filtered out
            my_assignments.append(assignment)

        for assignment_type in ("released", "fetched"):
            if held_assignments[assignment_type].items():
                for assignment_id in held_assignments[assignment_type]:
                    my_assignments.append(
                        held_assignments[assignment_type][assignment_id]
                    )

        if self.inbound or self.cached:
            _get_key = lambda info: (
                info["course_id"],
                info["student_id"],
                info["assignment_id"],
            )
            _match_key = lambda info, key: (
                info["course_id"] == key[0]
                and info["student_id"] == key[1]
                and info["assignment_id"] == key[2]
            )
            assignment_keys = sorted(
                list(set([_get_key(info) for info in my_assignments]))
            )
            assignment_submissions = []
            for key in assignment_keys:
                submissions = [x for x in my_assignments if _match_key(x, key)]
                submissions = sorted(submissions, key=lambda x: x["timestamp"])
                info = {
                    "course_id": key[0],
                    "student_id": key[1],
                    "assignment_id": key[2],
                    "status": submissions[0]["status"],
                    "submissions": submissions,
                }
                assignment_submissions.append(info)
            my_assignments = assignment_submissions

        return my_assignments

    def list_files(self):
        """List files"""
        self.log.info(f"ExchaneList.list_file starting")
        # TODO: this is a legacy option from ExchangeList and should be handled more elegantly
        if self.cached:
            return []

        assignments = self.parse_assignments()

        return assignments

    def remove_files(self):
        if self.course_id:
            """Delete assignment"""

            url = f"assignment?course_id={quote_plus(self.course_id)}&assignment_id={quote_plus(self.coursedir.assignment_id)}"

            r = self.api_request(url, method="DELETE")

            self.log.debug(f"Got back {r.status_code} after assignment unrelease")

    def start(self):
        if self.path_includes_course:
            self.coursedir.submitted_directory = os.path.join(
                self.course_id, "collected"
            )
            r = self.course_id
        else:
            self.coursedir.submitted_directory = "collected"
            r = "."
        self.log.debug(
            f"externalexchange.list.start - coursedir.submitted_directory = {self.coursedir.submitted_directory}"
        )
        self.fetched_root = os.path.abspath(os.path.join("", r))
        if self.remove:
            return self.remove_files()
        else:
            return self.list_files()
