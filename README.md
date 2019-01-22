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
    - [Deployment](#deployment)
        - [Local building](#local-building)

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
