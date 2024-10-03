import glob
import json
import os
from urllib.parse import quote_plus

import nbgrader.exchange.abc as abc
from nbgrader.exchange.default.list import ExchangeList as DefaultExchangeList
from traitlets import Unicode

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
        """
        This queries the database for all the assignments for a course

        if self.inbound or self.cached are true, it returns all the 'submitted'
        items, else it returns all the 'released' ones.

        (it doesn't care about feedback or collected actions)
        """
        if self.coursedir.course_id:
            """List assignments for specific course"""
            r = self.api_request(f"assignments?course_id={quote_plus(self.coursedir.course_id)}")
        else:
            """List assignments for all courses"""
            r = self.api_request("assignments")

        self.log.debug(f"Got back {r} when listing assignments")

        try:
            assignments = r.json()
        except json.decoder.JSONDecodeError:
            self.log.error("Got back an invalid response when listing assignments")
            return []

        return assignments["value"]

    def init_src(self):
        pass

    # sets self.assignments to be the list of assignment records that match the
    #  released/submitted/cached criteria configured
    def init_dest(self):
        self.assignments = []

        exchange_listed_assignments = self.query_exchange()
        self.log.debug(f"ExternalExchange.list.init_dest collected {exchange_listed_assignments}")

        # if "inbound", looking for inbound (submitted) records
        # elif 'cached', looking for already downloaded files
        # else, looking for outbound (released) files
        if self.inbound or self.cached:
            for assignment in exchange_listed_assignments:
                if assignment.get("status") == "submitted":
                    self.assignments.append(assignment)
        else:
            self.assignments = filter(lambda x: x.get["status"] == "released", exchange_listed_assignments)

    def copy_files(self):
        pass

    # Add the path for notebooks on disk, and add the blank parameters
    # Feedback details is listed in "submitted" records
    def parse_assignment(self, assignment):  # , on_disk_assignments=None):
        # If the assignment was found on disk, we need to expand the metadata
        if assignment.get("status") == "fetched":
            # get the individual notebook details
            assignment_dir = os.path.join(self.assignment_dir, assignment.get("assignment_id"))

            if self.path_includes_course:
                assignment_dir = os.path.join(
                    self.assignment_dir,
                    self.coursedir.course_id,
                    assignment.get("assignment_id"),
                )

            assignment["notebooks"] = []
            # Find the ipynb files
            for notebook in sorted(glob.glob(os.path.join(assignment_dir, "*.ipynb"))):
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

        return assignment

    def parse_assignments(self):
        # Set up some general variables
        self.assignments = []
        held_assignments = {"fetched": {}, "released": {}}

        # Get a list of everything from the exchange
        exchange_listed_assignments = self.query_exchange()

        # if "inbound" or "cached" are true, we're looking for inbound
        #  (submitted) records else we're looking for outbound (released)
        #  records
        # (everything else is irrelevant for this method)
        if self.inbound or self.cached:
            for assignment in exchange_listed_assignments:
                if assignment.get("status") == "submitted":
                    self.assignments.append(assignment)
        else:
            for assignment in exchange_listed_assignments:
                if assignment.get("status") == "released":
                    self.assignments.append(assignment)

        # We want to check the local disk for "fetched" items, not what the external server
        # says we should have
        interim_assignments = []
        found_fetched = set([])
        for assignment in self.assignments:
            assignment_directory = self.fetched_root + "/" + assignment.get("assignment_id")
            if assignment["status"] == "released":
                # Has this release already been found on disk?
                if assignment["assignment_id"] in found_fetched:
                    continue
                # Check to see if the 'released' assignment is on disk
                if os.path.isdir(assignment_directory):
                    assignment["status"] = "fetched"
                    # lets just take a note of having found this assignment
                    found_fetched.add(assignment["assignment_id"])

            interim_assignments.append(self.parse_assignment(assignment))
            self.log.debug(f"parse_assignment singular assignment returned: {assignment}")

        # now we build two sub-lists:
        # - the last "released" per assignment_id - but only if they've not been "fetched"
        #
        my_assignments = []
        for assignment in interim_assignments:
            # Skip those not being seen
            if assignment is None:
                continue

            # Hang onto the fetched assignment, if there is one
            # Note, we'll only have a note of the _first_ one - but that's fine
            #  as the timestamp is irrelevant... we just need to know if we
            #  need to look to the local disk
            if assignment.get("status") == "fetched":
                held_assignments["fetched"][assignment.get("assignment_id")] = assignment
                continue

            # filter out all the released items:
            if assignment.get("status") == "released":
                # This is complicated:
                #  - If the user has "fetched" the assignment, don't keep it
                #  - otherwise keep the latest one
                if assignment.get("assignment_id") in held_assignments["fetched"]:
                    continue
                else:
                    latest = held_assignments["released"].get(
                        assignment.get("assignment_id"),
                        {"timestamp": "1990-01-01 00:00:00"},
                    )
                    if assignment.get("timestamp") > latest.get("timestamp"):
                        held_assignments["released"][assignment.get("assignment_id")] = assignment
                    continue

            # "Submitted" assignments [may] have feedback
            # If they do, we need to promote details of local [on disk] feedback
            # to the "assignment" level. It would have been nice to match
            # sumbission times to feedback directories.
            # Note that the UI displays the "submitted" time in the table, but
            # will provide a link to a folder that is the "feedback" time
            # ("feedback-time" for all notebooks in one 'release' is the same)
            if assignment.get("status") == "submitted":
                assignment_dir = os.path.join(assignment.get("assignment_id"), "feedback")
                if self.path_includes_course:
                    assignment_dir = os.path.join(
                        self.coursedir.course_id,
                        assignment.get("assignment_id"),
                        "feedback",
                    )

                local_feedback_path = None
                has_local_feedback = False

                for notebook in assignment["notebooks"]:
                    nb_timestamp = notebook["feedback_timestamp"]

                    # This has to match timestamp in fetch_feedback.download
                    if nb_timestamp:
                        # get the individual notebook details
                        if os.path.isdir(
                            os.path.join(
                                assignment_dir,
                                nb_timestamp,
                            )
                        ):
                            local_feedback_path = os.path.join(
                                assignment_dir,
                                nb_timestamp,
                                f"{notebook['notebook_id']}.html",
                            )
                            has_local_feedback = os.path.isfile(
                                os.path.join(
                                    assignment_dir,
                                    nb_timestamp,
                                    f"{notebook['notebook_id']}.html",
                                )
                            )

                    notebook["has_local_feedback"] = has_local_feedback
                    notebook["local_feedback_path"] = local_feedback_path

                # Set assignment-level variables is any not the individual notebooks
                # have them
                if assignment["notebooks"]:
                    has_local_feedback = any([nb["has_local_feedback"] for nb in assignment["notebooks"]])
                    has_exchange_feedback = any([nb["has_exchange_feedback"] for nb in assignment["notebooks"]])
                    feedback_updated = any([nb["feedback_updated"] for nb in assignment["notebooks"]])
                else:
                    has_local_feedback = False
                    has_exchange_feedback = False
                    feedback_updated = False

                assignment["has_local_feedback"] = has_local_feedback
                assignment["has_exchange_feedback"] = has_exchange_feedback
                assignment["feedback_updated"] = feedback_updated
                if has_local_feedback:
                    assignment["local_feedback_path"] = os.path.join(
                        assignment_dir,
                        nb_timestamp,
                    )
                else:
                    assignment["local_feedback_path"] = None

                # We keep everything we've not filtered out
            my_assignments.append(assignment)

        # concatinate the "released" and "fetched" sublists to my_assignments
        for assignment_type in ("released", "fetched"):
            if held_assignments[assignment_type].items():
                for assignment_id in held_assignments[assignment_type]:
                    my_assignments.append(held_assignments[assignment_type][assignment_id])

        if self.inbound or self.cached:
            _get_key = lambda info: (  # noqa: E731 'do not assign a lambda expression, use a def'
                info["course_id"],
                info["student_id"],
                info["assignment_id"],
            )
            _match_key = lambda info, key: (  # noqa: E731 'do not assign a lambda expression, use a def'
                info["course_id"] == key[0] and info["student_id"] == key[1] and info["assignment_id"] == key[2]
            )
            assignment_keys = sorted(list(set([_get_key(info) for info in my_assignments])))
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
            my_assignments = [x for x in my_assignments if x.get("status") != "submitted"]

        return my_assignments

    def list_files(self):
        """List files"""
        self.log.debug("ExchaneList.list_file starting")

        assignments = self.parse_assignments()
        if self.inbound or self.cached:
            self.log.info("Submitted assignments:")
            for assignment in assignments:
                for info in assignment["submissions"]:
                    self.log.info(DefaultExchangeList.format_inbound_assignment(self, info))
        else:
            self.log.info("Released assignments:")
            for info in assignments:
                self.log.info(DefaultExchangeList.format_outbound_assignment(self, info))
        return assignments

    def remove_files(self):
        if self.coursedir.course_id:
            """Delete assignment"""
            self.log.info(
                f"Unreleasing assignment_id {self.coursedir.assignment_id} on course code {self.coursedir.course_id}"
            )

            url = f"assignment?course_id={quote_plus(self.coursedir.course_id)}&assignment_id={quote_plus(self.coursedir.assignment_id)}"  # noqa: E501

            r = self.api_request(url, method="DELETE")

            self.log.info(f"Got back {r.status_code} after assignment unrelease")

    def start(self):
        #####
        #
        # This is the code that changes the submitted directory
        #   away from default.
        # The feature flag NAAS_FEATURE_MULTI_MARKERS is also used
        #   to revert to default nbgrader behaviour
        # Once the feature flag becomes the default, `self.fetched_root`
        #   can be ditched
        #####
        if not os.environ.get("NAAS_FEATURE_MULTI_MARKERS"):
            if self.path_includes_course:
                self.coursedir.submitted_directory = os.path.join(self.coursedir.course_id, "collected")
            else:
                self.coursedir.submitted_directory = "collected"

        if self.path_includes_course:
            r = self.coursedir.course_id
        else:
            r = "."
        self.fetched_root = os.path.abspath(os.path.join("", r))

        if self.remove:
            return self.remove_files()
        else:
            return self.list_files()
