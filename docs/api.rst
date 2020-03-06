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
- [Local Testing](#local-testing)
    - [Local database](#local-database)
    - [Local building](#local-building)
    - [The Simple Development Cycle](#the-simple-development-cycle)
    - [The Notebook Client?](#the-notebook-client)
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

NBExchange is a Jupyterhub _service_, so `k8s-hub` installs it, and therefore deployed via `kubernetes-deployment`

# Local Testing

## Local database

The default, if you don't change it, database for nbexchange is an in-memory sqlite database.

This is almost certainly **NOT** what you actually want to use.

The the `NBEX_DB_URL` environment variable to set to something else (eg `NBEX_DB_URL = sqlite:///my_exchange_db.sqlite` or `NBEX_DB_URL = postgresql://user:pass@some_host:5432/my_db` )

## Local building

The code can be tested in `dummy-jupyterhub` - see the [Changing how plugins/extensions are installed](https://gitlab.edina.ac.uk/naas/dummy-jupyterhub/tree/configurable_nbexchange#changing-how-pluginsextensions-are-installed) section.

## The Simple Development Cycle

Using [`dummy-jupyterhub`](https://gitlab.edina.ac.uk/naas/dummy-jupyterhub) and it's very default notebook, you can ensure the code installs & performs as expected.

## The Notebook Client?

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

