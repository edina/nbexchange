[![coverage report](https://gitlab.edina.ac.uk/naas/nbexchange/badges/master/coverage.svg)](https://gitlab.edina.ac.uk/naas/nbexchange/commits/master)

# nbexchange

A Jupyterhub service that replaces the nbgrader Exchange.

<!-- TOC -->

- [nbexchange](#nbexchange)
    - [API Specification for the NBExchange service](#api-specification-for-the-nbexchange-service)
        - [Assignments](#assignments)
        - [Assignment](#assignment)
        - [Submission](#submission)
        - [Collections](#collections)
        - [Collection](#collection)
    - [Configuration](#configuration)
    - [Deployment](#deployment)
        - [Local building](#local-building)
- [Local Testing](#local-testing)
    - [Stage 1 - Have the code locally](#stage-1---have-the-code-locally)
    - [Stage 2 - installing from GitLab](#stage-2---installing-from-gitlab)
    - [Stage 3 - Is there a Notebook Client?](#stage-3---is-there-a-notebook-client)
- [Cluster testing](#cluster-testing)
- [Accepting a Merge Request](#accepting-a-merge-request)

<!-- /TOC -->

## API Specification for the NBExchange service

All URLs relative to `/services/nbexchange`

### Assignments

    .../assignments?course_id=$course_code

**GET**: returns list of assignments

Returns 
```
{"success": True,
    "value": [{
        "assignment_id": $assignment_code,
        "course_id": $course_code,
        "status": Str,
        "path": path,
        "notebooks": [{"name": x.name} for x in assignment.notebooks],
        "timestamp": action.timestamp.strftime(
            "%Y-%m-%d %H:%M:%S.%f %Z"
        ),
    },
    {},..
    ]}
```
or

    {"success": False, "note": $note}


### Assignment

    .../assignment?course_id=$course_code&assignment_id=$assignment_code

**GET**: downloads assignment

Returns binary data or raises Exception
     
**POST**: (role=instructor, with file): Add ("release") an assignment
returns

    {"success": True, "note": "Released"}

or raises Exception

### Submission

    .../submission?course_id=$course_code&assignment_id=$assignment_code

**POST**: stores the submission for that user
returns

    {"success": True, "note": "Released"}

or raises Exception

### Collections

    .../collections?course_id=$course_code&assignment_id=$assignment_code

**GET**: gets a list of submitted items
Return: _same as Assignments_

### Collection

    .../collections?course_id=$course_code&assignment_id=$assignment_code&path=$url_encoded_path

**GET**: downloads submitted assignment
Return: _same as Assignment_

## Configuration

The configuration for the hub service is part of `<ENV>_config` in `kubenetes_deployment`

## Deployment

The code is built into `k8s-hub`.

### Local building

The code can be tested in `dummy-jupyterhub`

# Local Testing

In the first instance, use the [`dummy-jupyterhub`](https://gitlab.edina.ac.uk/naas/dummy-jupyterhub) and it's very default notebook.

## Stage 1 - Have the code locally

Start with the code locally, then move it to it's own repo (as documetned in `dummy-jupyterhub`)

## Stage 2 - installing from GitLab

Once the main editing of the code is done, we need to add the code to GitLab.

Confirm you can install the extension from gitlab:

    RUN pip install -e git+https://gitlab+<token-username>:<token-password>@gitlab.edina.ac.uk/naas/my_extension@my_branch#egg=nbgrader

This will require 

1. A `setup.py` file, possibly more
1. A Deploy Token (GitLab: `Settings` -> `Repository` -> `Deploy Tokens`)

## Stage 3 - Is there a Notebook Client?

Once the extension installs from gitlab, try installing the client part into the `standard-notebook` (this will test that there are no spurious interactions with existing features) - do not commit or deploy the notebook at this time

# Cluster testing

At this point, follow the [k8s-hub documentation](../k8s-hub/README.md) for testing Jupyterhub on `dev`

You'll also want to follow the [notebook_extensions](../notebook_extensions/README.md) for the notebook-client extensions, if there are any

Once the code is ready for merging:

* Update the version number (so we can tell which version of the extension has been installed),
* Push all final commits,
* Issue Merge Request

# Accepting a Merge Request

Once the Merge Request for the extension code has been accepted, we need to also update the Notebooks:

* tag the new master commit in the extenstion repo with a version number (this is a git tag, as opposed to an image tag);
* The `k8s-hub` repo should have a branch related to this from the dev-testing above...
    * Check it out
    * update Dockerfile for new git-tag;
    * Follow the process for [issuing a new Merge Request](../k8s-hub/README.md) for the hub

