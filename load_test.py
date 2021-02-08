import argparse
import io
import json
import jwt
import os
import random
import re
import requests
import socket
import string
import sys
import tarfile

from datetime import datetime
from functools import partial
from kubernetes import client, config
from kubernetes.stream import portforward

from os import path
from urllib.parse import quote_plus
from urllib3.util import connection as urllib3_connection

"""
Workflow:

* set up a bunch of parameters for the run
  * get SECRET_KEY to match environment
  * get number of students to 
  * make random course_code
  * made random assignment_code

* create instructor identity
  * list assignments (needed to subscribe to course)
* instructor release assignment
* for each student identity
  * list assignments (needed to subscribe to course)
  * fetch assignment
  * submit assignment
* instructor collect assignments
* for each student identity
  * instructor releases feedback
* for each student identity
  * student collects feedback
* clear everything from the DB

Exchange-url defaults to dev, but can work in other clusters/namespaces
"""


class nbexchangeSoakTest:
    # command_line arguments
    args = argparse

    # These don't change
    service_url = "http://localhost:9000/services/nbexchange/"
    notebook_name = "test_1.ipynb"
    notebooks = ["test_1"]

    # These change each run
    assignment_id = str
    cluster = str
    course_id = str
    jwt_secret = str
    k8_api = client.CoreV1Api
    keep_db = bool
    namespace = str
    student_count = int
    student_list = list()
    exchange_server = str

    # This changes for each user!
    jwt_token = None

    def parse_args(self, args):
        parser = argparse.ArgumentParser(
            description="Arguments for nbexchange capacity-test."
        )
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
            help="The JWT token is encoded with a specific SECRET_KEY. This must match the environment you are testing. Defaults to the string 'asecretkey'",
        )
        parser.add_argument(
            "-k",
            "--keep_db",
            help="Whether to clear all the users & actions from the database or not. Defaults to False",
            action="store_true",
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
        parser.add_argument(
            "-v",
            "--verbose",
            type=int,
            choices=[0, 1, 2, 3],
            default=1,
            help="Be noisy when running [0 is completely silent, 3 is debug-level. defaults to 1].",
        )
        return parser.parse_args(args)

    def reporting(self, level, note):
        if level == "warn":
            if self.args.verbose >= 2:
                print(note)
        elif level == "debug":
            if self.args.verbose >= 3:
                print(note)
        else:
            if level == "info" and self.args.verbose:
                print(note)

    # code is [a-zA-Z][a-zA-Z0-9\ ]+[a-zA-Z]
    def id_generator(self, size=20, chars=string.ascii_letters + string.digits + " "):
        if size < 3:
            size = 3
        code = "".join(random.choice(chars) for _ in range(size - 2))
        return (
            random.choice(string.ascii_letters)
            + code
            + random.choice(string.ascii_letters)
        )

    def setup(self):
        self.args = self.parse_args(sys.argv[1:])
        self.reporting("debug", f"args: {self.args}")
        self.course_id = "made-up"  # self.id_generator()
        self.assignment_id = self.id_generator()

        self.cluster = self.args.cluster
        self.jwt_secret = self.args.jwt_secret
        self.namespace = self.args.namespace
        self.student_count = self.args.student_count
        self.reporting(
            "debug",
            f"class variables: course_id: {self.course_id}, assignment_id: {self.assignment_id}, cluster: {self.cluster}, namespace: {self.namespace}, jwt_secret: {self.jwt_secret}, student_count: {self.student_count}",
        )

        # Check we have some values
        if not (
            self.assignment_id,
            self.course_id,
            self.cluster,
            self.namespace,
            self.jwt_secret,
            self.student_count,
        ):
            sys.exit(
                "Missing a value from one of assignment_id, course_id, cluster, jwt_secret, namespace, student_count"
            )

        self.reporting("debug", "Poke the cluster to see what we can fine")
        # Can we contact the k8 cluster?
        contexts, active_context = config.list_kube_config_contexts()
        self.reporting(
            "debug",
            f"Your config knows about: contexts: {contexts}, active_context: {active_context}",
        )
        self.reporting("debug", f"Your active context is: {active_context}")
        if not contexts:
            sys.exit("Cannot find any context in kube-config file.")
        contexts = [context["name"] for context in contexts]
        self.reporting("debug", f"list of found contexts: {contexts}")

        if self.cluster not in contexts:
            sys.exit(f"{self.cluster} not in list of known clusters: {contexts}")
        self.reporting("debug", f"Confirming we can use {self.cluster}")

        config.load_kube_config(context=self.cluster)
        self.k8_api = client.CoreV1Api()
        pods = self.k8_api.list_namespaced_pod("default")
        self.reporting("debug", f"found pods: {pods}")
        items = list()
        for item in pods.items:
            if re.search(r"nbexchange", item.metadata.name):
                items.append(item)
        if not items:
            sys.exit(f"Failed to find an nbexchange server in the cluster")
        if len(items) > 1:
            sys.exit(f"There are too many exchange servers in the cluster: {items}")
        self.exchange_server = items[0].metadata.name
        self.reporting("debug", f"found exchange server: {self.exchange_server}")

        # We're good to go - make up the list of student named
        for i in range(1, self.student_count):
            self.student_list.append(f"1-s{i:06}")
        self.reporting("debug", f"created students: {self.student_list}")

        self.reporting("debug", f"setting up the port forwarding magick")
        # lifted from https://github.com/kubernetes-client/python/blob/master/examples/pod_portforward.py
        # Monkey patch urllib3.util.connection.create_connection
        def kubernetes_create_connection(*args, **kwargs):
            pf = portforward(
                self.k8_api.connect_get_namespaced_pod_portforward,
                self.exchange_server,
                self.namespace,
                ports="9000",
            )
            return pf.socket(9000)

        urllib3_connection.create_connection = kubernetes_create_connection
        self.reporting("debug", f"... done")

        self.reporting(
            "info",
            f"All good: Going to test {self.student_count} students in cluster '{self.cluster}', using nbexchange '{self.exchange_server}'",
        )
        self.reporting("debug", f"End of setup phase")

    def make_jwt_token(self, username, role):
        self.reporting(
            "debug", f"make_jwt_token called - username: {username}, role: {role}"
        )
        payload = {
            "username": username,
            "n_cid": self.course_id,
            "n_cnm": "My Funky Course",
            "n_rl": role,
            "n_oid": "1",
            "n_nb": "Standard service",
        }
        self.reporting(
            "debug", f"making jwt - payload: {payload}, secret: {self.jwt_secret}"
        )
        this_jwt_token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        self.reporting("debug", f"make_jwt_token returning token {this_jwt_token}")
        return this_jwt_token

    def api_request(self, path, method="GET", jwt_token=None, *args, **kwargs):
        cookies = dict()
        headers = dict()

        cookies["noteable_auth"] = jwt_token

        url = self.service_url + path
        self.reporting("warn", f"url: {url}, cookies: {cookies}")

        if method == "GET":
            get_req = partial(requests.get, url, headers=headers, cookies=cookies)
            return get_req(*args, **kwargs)
        elif method == "POST":
            post_req = partial(requests.post, url, headers=headers, cookies=cookies)
            return post_req(*args, **kwargs)
        elif method == "DELETE":
            delete_req = partial(requests.delete, url, headers=headers, cookies=cookies)
            return delete_req(*args, **kwargs)
        else:
            raise NotImplementedError(f"HTTP Method {method} is not implemented")

    def do_list(self, token):
        self.reporting("warn", f"do_list called - token: {token}")
        assignments = None

        r = self.api_request(
            f"assignments?course_id={quote_plus(self.course_id)}",
            jwt_token=token,
        )
        print(r.status_code)
        try:
            assignments = r.json()
        except json.decoder.JSONDecodeError:
            print(f"Got back an invalid response when listing assignments: {r.content}")
            return []
        self.reporting("debug", f"do_list found: {assignments}")
        self.reporting("warn", f"do_list finished")

    def instructor_release(self, username=None):
        self.reporting("warn", f"instructor_release called - username: {username}")
        user_jwt_token = self.make_jwt_token(username, "Instructor")
        self.reporting("warn", f"user_token: {user_jwt_token}")

        self.reporting("debug", f"do_list to subscribe instructor to course")
        # subscribe instructor to the course first.
        self.do_list(token=user_jwt_token)

        self.reporting("debug", f"make the tar file object")

        tar_file = io.BytesIO()

        with tarfile.open(fileobj=tar_file, mode="w:gz") as tar_handle:
            tar_handle.add(self.notebook_name, arcname=".")
        tar_file.seek(0)

        files = {"assignment": ("assignment.tar.gz", tar_file)}

        url = f"assignment?course_id={quote_plus(self.course_id)}&assignment_id={quote_plus(self.assignment_id)}"
        self.reporting("debug", f"call self.api_request")

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
            self.reporting("info", f"Release failed: {r.text}")
        print(data)
        if not data["success"]:
            self.reporting("info", f"Release failed: {data['note']}")
        self.reporting("info", f"Assignment released")

    def student_fetch(self, username=None):
        self.reporting("warn", f"student_fetch called - username: {username}")
        pass

    def student_submit(self, username=None):
        self.reporting("warn", f"student_submit called - username: {username}")
        pass

    def instructor_collect(self, username=None):
        self.reporting("warn", f"instructor_collect called - username: {username}")
        pass

    def instructor_release_feedback(self, username=None):
        self.reporting(
            "warn", f"instructor_release_feedback called - username: {username}"
        )
        pass

    def student_fetch_feedback(self, username=None):
        self.reporting("warn", f"student_fetch_feedback called - username: {username}")
        pass

    # This requires additional code in the handlers
    def tidy_up(self):
        self.reporting("warn", f"tidy_up called - keep_db?: {self.keep_db}")
        if not self.keep_db:
            pass

    def main(self):
        self.setup()

        # # this is just a check to make sure we're working
        # self.do_list(username="1-kiz", role="Instructor")

        # This will be the real start point
        self.instructor_release(username="1-instructor")

        # # In the simple model, everyone fetches then everyone submits
        # # In a more complex model, fetches, submissions, and even collections, could be interleaved
        # for student in self.student_list:
        #     self.student_fetch(username=student)
        #     self.student_submit(username=student)
        # self.instructor_collect(username="1-instructor")
        # self.instructor_release_feedback(username="1-instructor")

        # # In the simple model, everyone fetches feedback after it's been released for everyone
        # for student in self.student_list:
        #     self.student_fetch_feedback(username=student)

        # self.tidy_up()


if __name__ == "__main__":
    app = nbexchangeSoakTest()
    app.main()
