import glob
import json
import nbgrader.exchange.abc as abc
import os
import re
import sys

from traitlets import Bool, Unicode
from urllib.parse import quote_plus

from .exchange import Exchange


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

        self.assignments = []

        exchange_listed_assignments = self.query_exchange()
        self.log.debug(
            f"ExternalExchange.list.init_dest collected {exchange_listed_assignments}"
        )

        # if "inbound", looking for inbound (submitted) records
        # elif 'cached', looking for already downloaded files
        # else, looking for outbound (released) files
        if self.inbound or self.cached:
            for assignment in exchange_listed_assignments:
                if assignment.get("status") == "submitted":
                    self.assignments.append(assignment)
        else:
            self.assignments = exchange_listed_assignments

    def copy_files(self):
        pass

    def get_fetched_assignments(self):
        assignment_dir = ""

        if self.path_includes_course:
            assignment_dir = os.path.join(self.assignment_dir, self.course_id)
        else:
            assignment_dir = os.path.join(self.assignment_dir)

        dirs = [entry.path for entry in os.scandir(assignment_dir) if entry.is_dir() and re.match(r'[^\.]', entry.name)]
        return dirs

    ### We need to add feedback into submitted items
    ### (this may not be the best place to process them)
    def parse_assignment(self, assignment): #, on_disk_assignments=None):
        # For fetched & collected items - we want to know what the user has on-disk
        # rather than what the exchange server things we have.
        # if on_disk_assignments is not None:
        #     on_disk_assignment = on_disk_assignments.get(assignment.get("assignment_id"))
        #     if on_disk_assignment is None and assignment.get("status") == "fetched":
        #         assignment["status"] = "released"

        if assignment.get("status") in ("fetched", "collected"):
            assignment_dir = os.path.join(self.assignment_dir, assignment.get("assignment_id"))

            if self.path_includes_course:
                assignment_dir = os.path.join(self.assignment_dir, self.course_id, assignment.get("assignment_id"))

            print(f"plugin/list.parse_assignment looking in {assignment_dir}")
            assignment["notebooks"] = []
            # Find the ipynb files
            for notebook in sorted(
                glob.glob(os.path.join(assignment_dir, "*.ipynb"))
            ):
                notebook_id = os.path.splitext(os.path.split(notebook)[1])[0]
                assignment["notebooks"].append(
                    {
                        "path": notebook,
                        "name": notebook_id,
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
        print("list.parse_assignments called")
        course_id = self.course_id if self.course_id and self.course_id != "*" else None
        assignment_id = (
            self.coursedir.assignment_id
            if self.coursedir.assignment_id and self.coursedir.assignment_id != "*"
            else None
        )
        student_id = (
            self.coursedir.student_id
            if self.coursedir.student_id and self.coursedir.student_id != "*"
            else None
        )
        self.assignments = []
        remote_assignments = self.query_exchange()

        # on_disk_assignments = self.get_fetched_assignments()
        # self.log.debug(
        #     f"ExternalExchange.list.parse_assignments collected {remote_assignments}"
        # )
        print(f"* remote: {remote_assignments}")
        # print(f"* local: {on_disk_assignments}")
        # if "inbound" or "cached", looking for inbound (submitted) records
        # else, looking for outbound (released) files
        print(f"inbound: {self.inbound}; cached: {self.cached}")
        if self.inbound or self.cached:
            print(
                f"'assignments' being set to just the remote-assignments tagged 'submitted'"
            )
            for assignment in remote_assignments:
                if assignment.get("status") == "submitted":
                    self.assignments.append(assignment)
        else:
            print(f"'assignments' being set to remote-assignments")
            self.assignments = remote_assignments
        # self.assignments = self.query_exchange()  # This should really set by init_dest

        # We want to check the local disk for "fetched" items, not what the external server
        # says we should have
        print(f"modify each 'assignment' in view of what we have in local assignments")
        interim_assignments = []
        for assignment in self.assignments:
            interim_assignments.append(
                self.parse_assignment(assignment) #, on_disk_assignments)
            )
            self.log.info(
                f"parse_assignment singular assignment returned: {assignment}"
            )
        print(f"interim_assignments: {interim_assignments}")

        # now we build three sub-lists:
        # - one "fetched" per assignment_id
        # - the last "released" per assignment_id - but only if they've not been "fetched"
        # - all "collected"
        # - all "submitted"
        held_assignments = {"fetched": {}, "released": {}}
        my_assignments = []
        for assignment in interim_assignments:
            print(f"> this assignment starts as: {assignment}")
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
                print(
                    f">> this assignment is {assignment.get('status')}, and needs checking"
                )
                # This is complicated:
                #  - If the user has "fetched" the assignment, and the asignment directory is on disk
                #    ... don't keep it
                #  - otherwise keep the latest one
                if assignment.get("assignment_id") in self.seen_assignments[
                    "fetched"
                ] and os.path.isdir(assignment_directory):
                    print(
                        f">>> this assignment has been tagged as fetched, and exists on disk - skip"
                    )
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
                    print(
                        f">>> this assignment is a newest version we've seen, hang onto it"
                    )
                    continue

            # "Submitted" assignments [may] have feedback
            if assignment.get("status") in ["released", "submitted"]:
                print(
                    f">> this assignment is {assignment.get('status')}, and we need to look for feedback"
                )
                local_feedback_dir = None
                for notebook in assignment["notebooks"]:
                    feedback_timestamp = str(notebook["feedback_timestamp"])
                    local_feedback_dir = os.path.relpath(
                        os.path.join(
                            assignment_directory, "feedback", feedback_timestamp
                        )
                    )
                    local_feedback_path = os.path.join(
                        local_feedback_dir, "{0}.html".format(notebook["name"])
                    )
                    has_local_feedback = os.path.isfile(local_feedback_path)
                    notebook["has_local_feedback"] = has_local_feedback
                    notebook["local_feedback_path"] = local_feedback_path
                    print(
                        f">>> feedback_timestamp: {feedback_timestamp}; local_feedback_dir: {local_feedback_dir}"
                    )

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
                print(
                    f">>> has_local_feedback: {has_local_feedback}; has_exchange_feedback: {has_exchange_feedback}; feedback_updated: {feedback_updated}"
                )
                assignment["has_local_feedback"] = has_local_feedback
                assignment["has_exchange_feedback"] = has_exchange_feedback
                assignment["feedback_updated"] = feedback_updated
                assignment["local_feedback_path"] = local_feedback_dir
                # We keep everything we've not filtered out
            print(f"> this assignment ends up as: {assignment}")
            my_assignments.append(assignment)
        print(f"my_assignments: {my_assignments}")
        print(f"held_assignments: {held_assignments}")

        for assignment_type in ("released", "fetched"):
            if held_assignments[assignment_type].items():
                for assignment_id in held_assignments[assignment_type]:
                    my_assignments.append(
                        held_assignments[assignment_type][assignment_id]
                    )
        print(f"my_assignments: {my_assignments}")
        print(f"held_assignments: {held_assignments}")

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
        else:
            my_assignments = [
                x for x in my_assignments if x.get("status") != "submitted"
            ]

        print(f"my_assignments: {my_assignments}")
        return my_assignments

    def list_files(self):
        """List files"""
        self.log.info(f"ExchaneList.list_file starting")
        # TODO: this is a legacy option from ExchangeList and should be handled more elegantly
        # if self.cached:
        #     return []
        print("list.list_files called")

        assignments = self.parse_assignments()

        return assignments

    def remove_files(self):
        if self.course_id:
            """Delete assignment"""

            url = f"assignment?course_id={quote_plus(self.course_id)}&assignment_id={quote_plus(self.coursedir.assignment_id)}"

            r = self.api_request(url, method="DELETE")

            self.log.debug(f"Got back {r.status_code} after assignment unrelease")

    def start(self):
        print("list.start called")
        print(f"submitted_directory = {self.coursedir.submitted_directory}")
        if self.path_includes_course:
            self.coursedir.submitted_directory = os.path.join(
                self.course_id, "collected"
            )
            r = self.course_id
        else:
            self.coursedir.submitted_directory = "collected"
            r = "."

        self.log.info(
            f"externalexchange.list.start - coursedir.submitted_directory = {self.coursedir.submitted_directory}"
        )
        self.fetched_root = os.path.abspath(os.path.join("", r))
        if self.remove:
            return self.remove_files()
        else:
            print("returning a list")
            return self.list_files()
