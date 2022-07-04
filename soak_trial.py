import argparse
import base64
import glob
import hashlib
import io
import json
import logging
import os
import re
import shutil
import sys
import tarfile
import time
import uuid
from contextlib import closing
from datetime import datetime
from functools import partial
from urllib.parse import quote_plus

import jwt
import requests
from kubernetes import client, config


class nbexchangeSoakTest:
    # command_line arguments
    args = argparse

    # These don't change
    service_url = "http://localhost:9000/services/nbexchange/"
    feedback_name = "test_1.html"
    notebook_name = "test_1.ipynb"
    data_file = "sample_data.csv"
    notebooks = ["test_1"]

    # These change each run
    assignment_code = str
    course_code = str
    exchange_server = str
    log = logging
    k8_api = client.CoreV1Api
    student_list = list()

    # This changes for each user!
    jwt_token = None

    def parse_args(self, args):
        parser = argparse.ArgumentParser(description="Arguments for nbexchange capacity-test.")
        parser.add_argument(
            "-c",
            "--cluster",
            type=str,
            default="noteable-dev",
            help="The kubernetes cluster to use. Defaults to noteable-dev.",
        )
        parser.add_argument(
            "-j",
            "--jwt_secret",
            type=str,
            default="asecretkey",
            help="The JWT token is encoded with a specific SECRET_KEY. This must match the environment you are testing. Defaults to the highly imaginative 'asecretkey'",  # noqa: E501
        )
        parser.add_argument(
            "-k",
            "--keep_data",
            help="Whether to clear all the users & actions from the database (and files from disk) or not. Defaults to False - purge",  # noqa: E501
            action="store_true",
        )
        parser.add_argument(
            "-l",
            "--log",
            type=str,
            choices=["info", "warn", "warning", "error", "debug", "critical"],
            default="info",
            help="Logging level, defaults to 'info'",
        )
        parser.add_argument(
            "-n",
            "--namespace",
            type=str,
            default="default",
            help="The namespace in the cluster to use. Defaults to 'default'",
        )
        parser.add_argument(
            "-s",
            "--student_count",
            type=int,
            default=250,
            help="The number of students out soak-test is going to use. Defaults to 250.",
        )
        return parser.parse_args(args)

    def setup(self):
        self.args = self.parse_args(sys.argv[1:])
        levels = {
            "critical": logging.CRITICAL,
            "error": logging.ERROR,
            "warn": logging.WARNING,
            "warning": logging.WARNING,
            "info": logging.INFO,
            "debug": logging.DEBUG,
        }
        logging.basicConfig(
            level=levels[self.args.log.lower()],
            format="%(asctime)s,%(msecs)d %(levelname)-8s [%(pathname)s:%(lineno)d in function %(funcName)s] %(message)s",  # noqa: E501
            datefmt="%Y-%m-%d:%H:%M:%S",
        )
        self.log = logging.getLogger(__name__)

        self.log.debug(f"args: {self.args}")
        self.course_code = str(uuid.uuid4())
        self.assignment_code = str(uuid.uuid4())

        self.log.debug(
            f"class variables: course_code: {self.course_code}, assignment_code: {self.assignment_code}, cluster: {self.args.cluster}, namespace: {self.args.namespace}, jwt_secret: {self.args.jwt_secret}, student_count: {self.args.student_count}",  # noqa: E501
        )

        # Check we have some values
        if not (
            self.assignment_code,
            self.course_code,
            self.args.cluster,
            self.args.namespace,
            self.args.jwt_secret,
            self.args.student_count,
        ):
            sys.exit(
                "Missing a value from one of assignment_code, course_code, cluster, jwt_secret, namespace, student_count"  # noqa: E501
            )

        self.log.debug("Poke the cluster to see what we can fine")
        # Can we contact the k8 cluster?
        contexts, active_context = config.list_kube_config_contexts()
        self.log.debug(
            f"Your config knows about: contexts: {contexts}, active_context: {active_context}",
        )
        self.log.debug(f"Your active context is: {active_context}")
        if not contexts:
            sys.exit("Cannot find any context in kube-config file.")
        contexts = [context["name"] for context in contexts]
        self.log.debug(f"list of found contexts: {contexts}")

        if self.args.cluster not in contexts:
            sys.exit(f"{self.args.cluster} not in list of known clusters: {contexts}")
        self.log.debug(f"Confirming we can use {self.args.cluster}")

        config.load_kube_config(context=self.args.cluster)
        self.k8_api = client.CoreV1Api()
        pods = self.k8_api.list_namespaced_pod(self.args.namespace)
        self.log.debug(f"found pods: {pods}")
        items = list()
        for item in pods.items:
            if re.search(r"nbexchange", item.metadata.name):
                items.append(item)
        if not items:
            sys.exit("Failed to find an nbexchange server in the cluster")
        if len(items) > 1:
            sys.exit(f"There are too many exchange servers in the cluster: {items}")
        self.exchange_server = items[0].metadata.name
        self.log.debug(f"found exchange server: {self.exchange_server}")

        # We're good to go - make up the list of student named
        for i in range(1, self.args.student_count + 1):
            self.student_list.append(f"1-s{i:06}")
        self.log.debug(f"created students: {self.student_list}")

        # Check for k8 port-forwarding, and ask for it to be set up if needed
        # ### I really wish this had worked..... but it just times out.
        # self.log.debug(f"setting up the port forwarding magick")
        # # lifted from https://github.com/kubernetes-client/python/blob/master/examples/pod_portforward.py
        # # Monkey patch urllib3.util.connection.create_connection
        # def kubernetes_create_connection(*args, **kwargs):
        #     pf = portforward(
        #         self.k8_api.connect_get_namespaced_pod_portforward,
        #         self.exchange_server,
        #         self.args.namespace,
        #         ports="9000",
        #     )
        #     return pf.socket(9000)
        # urllib3_connection.create_connection = kubernetes_create_connection
        # self.log.debug(f"... done")
        # ###
        # ## port forwarding, hack starts
        print("\nSet up port forwarding")
        try:
            url = ""
            self.log.debug("call self.api_request")
            self.log.disabled = True
            r = self.api_request(
                url,
                method="GET",
            )
            self.log.disabled = False
            if r.status_code == 200:
                print(
                    "## *NOTE*: Got a response from *something* on port 9000, please confirm it's the Kubernetes proxy we want ##"  # noqa: E501
                )
                print(
                    "##         If not, remove it... and follow the commands below..                                           ##"  # noqa: E501
                )
        except Exception:
            pass
        print("Please open a new terminal and run the following command(s):\n")
        if active_context["name"] != self.args.cluster:
            print(f"    kubectl config use-context {self.args.cluster}")
        print(f"    kubectl port-forward pod/{self.exchange_server}  9000:9000\n")
        input(".... and wait for the command to say it's forwarding - then press enter here to continue")
        # ## port forwarding, hack ends

        self.log.info(
            f"Looking good: Going to test {self.args.student_count} students in cluster '{self.args.cluster}', using nbexchange '{self.exchange_server}'",  # noqa: E501
        )
        self.log.info("End of setup phase")

    def make_jwt_token(self, username, role):
        self.log.debug(f"make_jwt_token called - username: {username}, role: {role}")
        payload = {
            "username": username,
            "n_cid": self.course_code,
            "n_cnm": "My Funky Course",
            "n_rl": role,
            "n_oid": "1",
            "n_nb": "Standard service",
        }
        self.log.debug(f"making jwt - payload: {payload}, secret: {self.args.jwt_secret}")
        this_jwt_token = jwt.encode(payload, self.args.jwt_secret, algorithm="HS256").decode("UTF-8")
        self.log.debug(f"make_jwt_token returning token {this_jwt_token}")
        return this_jwt_token

    def api_request(self, path, method="GET", jwt_token=None, *args, **kwargs):
        self.log.debug(f"api_request called. method:{method}, path:{path}, jwt_token:{jwt_token}")

        cookies = dict()
        headers = dict()

        cookies["noteable_auth"] = jwt_token

        url = self.service_url + path
        self.log.debug(f"url: {url}, cookies: {cookies}")

        try:
            if method == "GET":
                get_req = partial(requests.get, url, headers=headers, cookies=cookies)
                self.log.debug("make GET request")
                return get_req(*args, **kwargs)
            elif method == "POST":
                post_req = partial(requests.post, url, headers=headers, cookies=cookies)
                self.log.debug("make POST request")
                return post_req(*args, **kwargs)
            elif method == "DELETE":
                self.log.debug("make DELETE request")
                delete_req = partial(requests.delete, url, headers=headers, cookies=cookies)
                return delete_req(*args, **kwargs)
            else:
                raise NotImplementedError(f"HTTP Method {method} is not implemented")
        except Exception as e:  # TODO: exception handling
            self.log.exception(e)

    def instructor_release(self, username=None):
        self.log.info(f"instructor_release called - username: {username}")
        if username:

            user_jwt_token = self.make_jwt_token(username, "Instructor")
            self.log.debug(f"user_token: {user_jwt_token}")

            self.log.debug("make the tar file object")
            tar_file = io.BytesIO()

            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add("soak_trial_data/released", arcname=".")
            tar_file.seek(0)

            files = {"assignment": ("assignment.tar.gz", tar_file)}
            url = (
                f"assignment?course_id={quote_plus(self.course_code)}&assignment_id={quote_plus(self.assignment_code)}"
            )
            self.log.debug("call self.api_request")

            r = self.api_request(
                url,
                method="POST",
                jwt_token=user_jwt_token,
                data={"notebooks": self.notebooks},
                files=files,
            )
            data = None
            try:
                data = r.json()
            except json.decoder.JSONDecodeError:
                self.log.warning(f"Release failed: {r.text}")
            if not data["success"]:
                self.log.info(f"Release failed: {data['note']}")
            if data != {"success": True, "note": "Released"}:
                self.log.warning(f"Release response not as expects: {data} != {{'success': True, 'note': 'Released'}}")
        self.log.info("Assignment released")

    def student_fetch(self, username=None):
        self.log.info(f"student_fetch called - username: {username}")
        if username:
            unpack_dir = os.path.join(
                "/tmp/load_test/students",
                self.assignment_code,
                username,
            )
            os.makedirs(unpack_dir, exist_ok=True)
            self.log.debug(f"made directory {unpack_dir}")

            user_jwt_token = self.make_jwt_token(username, "Student")
            self.log.debug(f"user_token: {user_jwt_token}")

            r = self.api_request(
                f"assignment?course_id={quote_plus(self.course_code)}&assignment_id={quote_plus(self.assignment_code)}",
                jwt_token=user_jwt_token,
            )
            self.log.debug(f"Got back {r.status_code}  {r.headers['content-type']} after file download")
            tgz = r.content
            try:
                tar_file = io.BytesIO(tgz)
                with tarfile.open(fileobj=tar_file) as handle:
                    handle.extractall(path=unpack_dir)
            except Exception as e:
                self.log.exception(e)
            else:
                self.log.debug("data unpacked")

                found_files = os.listdir(str(unpack_dir))
                if sorted(found_files) != sorted([self.notebook_name, self.data_file]):
                    self.log.warning(
                        f"Student {username} failed to unpack assignment {self.assignment_code} into {unpack_dir} - seeing {found_files}"  # noqa: E501
                    )
        self.log.info("student_fetch done")

    def student_submit(self, username=None):
        self.log.info(f"student_submit called - username: {username}")
        if username:

            unpack_dir = os.path.join(
                "/tmp/load_test/students",
                self.assignment_code,
                username,
            )
            if not os.path.isdir(unpack_dir):
                self.log.warning(f"unable to find {unpack_dir}")
                return

            user_jwt_token = self.make_jwt_token(username, "Student")
            self.log.debug(f"user_token: {user_jwt_token}")

            # timestamp format has to match the exchange, for veracity
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f %Z").strip()
            tar_file = io.BytesIO()
            self.log.debug(f"make the tar file object (with timestamp.txt file {timestamp})")

            with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
                tar_handle.add(unpack_dir, arcname=".")
                with closing(io.BytesIO(timestamp.encode())) as fobj:
                    tarinfo = tarfile.TarInfo("timestamp.txt")
                    tarinfo.size = len(fobj.getvalue())
                    tarinfo.mtime = time.time()
                    tar_handle.addfile(tarinfo, fileobj=fobj)
            tar_file.seek(0)

            files = {"assignment": ("assignment.tar.gz", tar_file)}
            url = (
                f"submission?course_id={quote_plus(self.course_code)}&assignment_id={quote_plus(self.assignment_code)}"
            )
            self.log.debug("call self.api_request")

            r = self.api_request(
                url,
                method="POST",
                jwt_token=user_jwt_token,
                data={"notebooks": self.notebooks},
                files=files,
            )
            data = None
            try:
                data = r.json()
            except json.decoder.JSONDecodeError:
                self.log.warning(f"Release failed: {r.text}")
            if not data["success"]:
                self.log.info(f"Release failed: {data['note']}")
            if data != {"success": True, "note": "Submitted"}:
                self.log.warning(f"Release response not as expects: {data} != {{'success': True, 'note': 'Submitted'}}")
        self.log.info("student_submit done")

    # This is a tad complex: it has to get the list of submissions, and then
    # loop over them, downloading each one in turn
    def instructor_collect(self, username=None):
        self.log.info(f"instructor_collect called - username: {username}")
        if username:
            user_jwt_token = self.make_jwt_token(username, "Instructor")
            self.log.debug(f"user_token: {user_jwt_token}")

            # Get a list of submissions
            self.log.debug("get a listing of collectable assignments")
            url = (
                f"collections?course_id={quote_plus(self.course_code)}&assignment_id={quote_plus(self.assignment_code)}"
            )
            r = self.api_request(url, jwt_token=user_jwt_token)
            self.log.debug(f"Got back {r} when listing collectable assignments")

            try:
                data = r.json()
            except json.decoder.JSONDecodeError:
                self.log.error("Got back an invalid response when listing assignments")
                return []

            if not data["success"]:
                self.log.error("Error looking for assignments to collect")
                return []

            submissions = data["value"]

            self.log.debug(f"Found the following items: {submissions}")

            if len(submissions) == 0:
                self.log.warning(f"No submissions of '{self.assignment_code}' to collect")
            else:
                self.log.debug(f"Processing {len(submissions)} submissions of '{self.assignment_code}'")

            for submission in submissions:

                # Work out the user-name from the path:
                # '/some/path/submitted/course_2/tree 1/1_kiz/1544109991/fdc8c4ae-b3e0-4db6-859d-17852d65ec08.gz'
                regex = (
                    "/submitted/" + re.escape(self.course_code) + "/" + re.escape(self.assignment_code) + "/([^/]+)/"
                )
                m = re.search(regex, submission["path"])
                if m:
                    student_id = m.group(1)  # m.group(0) is the whole regex match

                    if student_id:
                        local_dest_path = os.path.join(
                            "/tmp/load_test/collected",
                            self.assignment_code,
                            student_id,
                        )
                        os.makedirs(local_dest_path, exist_ok=True)

                        self.log.debug(f"collect {submission} to {local_dest_path}")
                        r = self.api_request(
                            f"collection?course_id={quote_plus(self.course_code)}&assignment_id={quote_plus(self.assignment_code)}&path={quote_plus(submission['path'])}",  # noqa: E501
                            jwt_token=user_jwt_token,
                        )
                        self.log.debug(f"Got back {r.status_code}  {r.headers['content-type']} after file download")
                        tgz = r.content

                        try:
                            tar_file = io.BytesIO(tgz)
                            with tarfile.open(fileobj=tar_file) as handle:
                                handle.extractall(path=local_dest_path)
                        except Exception as e:
                            if hasattr(e, "message"):
                                self.log.warning(e.message)
                            else:
                                self.log.warning(e)
                        found_files = os.listdir(str(local_dest_path))
                        if sorted(found_files) != sorted([self.notebook_name, self.data_file, "timestamp.txt"]):
                            self.log.warning(
                                f"Instructor {username} failed to unpack assignment {self.assignment_code} for {student_id} into {local_dest_path} - seeing {found_files}"  # noqa: E501
                            )
                        else:
                            self.log.info(f"collected {student_id}")

                        # collect also fakes the autograde & generate feedback, so
                        # needs to get the timestamp from the appropriate student
                        # under 'collected' the test_1.html demo file from
                        # 'soak_trial_data/feedback and put them in an individual
                        # student directory under 'feedback'
                        self.log.debug("Now to mock the result of 'authgrade' and 'generate_feedback' for the student")
                        local_feedback_path = os.path.join(
                            "/tmp/load_test/feedback",
                            self.assignment_code,
                            student_id,
                        )
                        os.makedirs(local_feedback_path, exist_ok=True)
                        self.log.debug("copy timestamp file")
                        try:
                            src = os.path.join(local_dest_path, "timestamp.txt")
                            dest = os.path.join(local_feedback_path, "timestamp.txt")
                            self.log.debug(f"copy {src} to {local_feedback_path}")
                            shutil.copyfile(src, dest)
                        except Exception as e:
                            if hasattr(e, "message"):
                                self.log.warning(e.message)
                            else:
                                self.log.warning(e)
                        self.log.debug("copy html file")
                        try:
                            src = os.path.join("soak_trial_data/feedback", self.feedback_name)
                            dest = os.path.join(local_feedback_path, self.feedback_name)
                            self.log.debug(f"copy {src} to {dest}")
                            shutil.copyfile(src, dest)
                        except Exception as e:
                            if hasattr(e, "message"):
                                self.log.warning(e.message)
                            else:
                                self.log.warning(e)
                        self.log.debug("check files were copied..")
                        found_files = os.listdir(str(local_feedback_path)).sort()
                        if found_files != [self.feedback_name, "timestamp.txt"].sort():
                            self.log.warning(
                                f"Failed to fake feedback into {local_feedback_path} - seeing {found_files}"
                            )

        self.log.info("instructor_collect done")

    # feedback was generated by the collect process
    def instructor_release_feedback(self, username=None):
        self.log.info(f"instructor_release_feedback called - username: {username}")
        if username:

            local_feedback_path = os.path.join(
                "/tmp/load_test/feedback",
                self.assignment_code,
                "*",
            )

            user_jwt_token = self.make_jwt_token(username, "Instructor")
            self.log.debug(f"user_token: {user_jwt_token}")

            html_files = glob.glob(os.path.join(local_feedback_path, "*.html"))
            self.log.debug(f"html files: {html_files}")
            for html_file in html_files:
                self.log.debug(f"this html file: {html_file}")
                regexp = re.escape(os.path.sep).join(
                    [
                        os.path.normpath(
                            os.path.join(
                                "/tmp/load_test/feedback",
                                self.assignment_code,
                                "(?P<student_id>.*)",
                            )
                        ),
                        "(?P<notebook_id>.*).html",
                    ]
                )
                self.log.debug(f"regex: {regexp} on html_file: {html_file}")

                m = re.match(regexp, html_file)
                if m is None:
                    msg = "Could not match '%s' with regexp '%s'" % (html_file, regexp)
                    self.log.error(msg)
                    continue

                gd = m.groupdict()
                student_id = gd["student_id"]
                notebook_id = gd["notebook_id"]
                self.log.debug(f"student_id: {student_id}, notebook_id: {notebook_id}")

                feedback_dir = os.path.split(html_file)[0]
                submission_dir = os.path.join(
                    "/tmp/load_test/collected",
                    self.assignment_code,
                    student_id,
                )
                self.log.debug(f"feedback_dir: {feedback_dir}, feedback_dir: {feedback_dir}")

                timestamp = open(os.path.join(feedback_dir, "timestamp.txt")).read().strip()
                nbfile = os.path.join(submission_dir, "{}.ipynb".format(notebook_id))
                unique_key = "+".join(
                    [
                        self.course_code,
                        self.assignment_code,
                        notebook_id,
                        student_id,
                        timestamp,
                    ]
                )

                self.log.debug("Unique key is: {}".format(unique_key))
                m = hashlib.md5()
                m.update(open(nbfile, "rb").read())
                if unique_key:
                    m.update(unique_key.encode("utf-8"))
                checksum = m.hexdigest()

                release_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f %Z").strip()

                self.log.info(
                    "Releasing feedback for student '{}' on assignment '{}/{}/{}' ({})".format(
                        student_id,
                        self.course_code,
                        self.assignment_code,
                        notebook_id,
                        release_timestamp,
                    )
                )

                with open(html_file) as feedback_file:
                    files = {"feedback": ("feedback.html", feedback_file.read())}

                url = (
                    f"feedback?course_id={quote_plus(self.course_code)}"
                    f"&assignment_id={quote_plus(self.assignment_code)}"
                    f"&notebook={quote_plus(notebook_id)}"
                    f"&student={quote_plus(student_id)}"
                    f"&timestamp={quote_plus(release_timestamp)}"
                    f"&checksum={quote_plus(checksum)}"
                )

                r = self.api_request(url, method="POST", files=files, jwt_token=user_jwt_token)

                self.log.debug(f"Got back {r.status_code} after feedback upload")
                data = None
                try:
                    data = r.json()
                except json.decoder.JSONDecodeError:
                    self.log.warning(r.text)

                if not data["success"]:
                    self.log.warning(data["note"])

                if data != {"success": True, "note": "Feedback released"}:
                    self.log.warning(
                        f"Release response not as expects: {data} != {{'success': True, 'note': 'Feedback released'}}"
                    )

                self.log.info(f"Uploaded feedback for {student_id} on assignment {self.assignment_code}.")

        self.log.info("instructor_release_feedback done")

    def student_fetch_feedback(self, username=None):
        self.log.info(f"student_fetch_feedback called - username: {username}")

        if username:

            user_jwt_token = self.make_jwt_token(username, "Student")
            self.log.debug(f"user_token: {user_jwt_token}")

            download_dir = os.path.join(
                "/tmp/load_test/students",
                self.assignment_code,
                "feedback",
                username,
            )
            os.makedirs(download_dir, exist_ok=True)
            self.log.debug(f"base fetch-feedback dir: {download_dir}")
            r = self.api_request(
                f"feedback?course_id={quote_plus(self.course_code)}&assignment_id={quote_plus(self.assignment_code)}",
                jwt_token=user_jwt_token,
            )
            self.log.debug(f"Got back {r.status_code} {r.headers['content-type']} after file download")
            content = r.json()

            # Feedback, here, is the time the feedback was generated, not the time of the submission
            if "feedback" in content:
                for f in content["feedback"]:
                    self.log.debug(f"fetch-feedback.download has {f['filename']}, {f['timestamp']}")
                    timestamp = f["timestamp"]
                    student_feedback_dir = os.path.join(download_dir, timestamp)
                    os.makedirs(student_feedback_dir, exist_ok=True)
                    try:
                        self.log.debug(f"fetch-feedback.download writing to {student_feedback_dir}")
                        with open(os.path.join(student_feedback_dir, f["filename"]), "wb") as handle:
                            handle.write(base64.b64decode(f["content"]))
                    except Exception as e:
                        self.log.debug(str(e))
                    found_files = os.listdir(str(student_feedback_dir))
                    if found_files != [self.feedback_name]:
                        self.log.warning(
                            f"Student {username} failed to fetch feedback for {self.assignment_code} into {student_feedback_dir} - seeing {found_files}"  # noqa: E501
                        )
            else:
                self.log.debug(content.get("note", "could not get feedback"))

        self.log.info("student_fetch_feedback done")

    # This requires additional code in the handlers
    def tidy_up(self, username=None):
        self.log.info(f"Tidy_up called: assignment_id={self.assignment_code} (keep_data?: {self.args.keep_data})")
        if username:

            user_jwt_token = self.make_jwt_token(username, "Instructor")

            url = (
                f"assignment?course_id={quote_plus(self.course_code)}&assignment_id={quote_plus(self.assignment_code)}"
            )
            if not self.args.keep_data:
                self.log.info("We're purging the data.... so deleting files too")
                url += "&purge=True"
                path = "/tmp/load_test"
                if os.path.isdir(path):
                    shutil.rmtree(path)

            self.log.debug(f"call self.api_request with url: {url}")

            self.api_request(
                url,
                method="DELETE",
                jwt_token=user_jwt_token,
            )
        self.log.info("tidy_up ended")

    def main(self):
        self.setup()

        try:
            self.log.info("Instructor Release")
            self.instructor_release(username="1-instructor")

            # In the simple model, everyone these all run sequentially
            # In a more complex [ie, real-file] model, fetches, submissions,
            # collections, and the feedback cycle all happen in an
            # interleaved manner.
            self.log.info("Students fetch and submit")
            for student in self.student_list:
                self.student_fetch(username=student)
                self.student_submit(username=student)
            self.instructor_collect(username="1-instructor")
            self.instructor_release_feedback(username="1-instructor")

            # In the simple model, everyone fetches feedback after it's been released for everyone
            for student in self.student_list:
                self.student_fetch_feedback(username=student)
            self.log.info(
                f"Finished: An assignment with {self.args.student_count} students has done 'release_assignment', 'fetch_assignment', 'submit', 'collect', 'release_feedback', and 'fetch_assignment'.",  # noqa: E501
            )
        except Exception:
            self.log.warning("Something went wrong... still tidying up though")
        self.tidy_up(username="1-instructor")
        self.log.warning(
            f"""
        SQL Tidy-up instructions, until the new 'purge' code is in the exchange
            delete from from assignment where assignment_code = '{self.assignment_code}';
        """
        )


if __name__ == "__main__":
    app = nbexchangeSoakTest()
    app.main()
