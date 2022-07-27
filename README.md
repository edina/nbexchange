![Linted](https://github.com/edina/nbexchange/workflows/Linted/badge.svg?branch=prepare_for_public_release)
[![codecov](https://codecov.io/gh/edina/nbexchange/branch/prepare_for_public_release/graph/badge.svg)](https://codecov.io/gh/edina/nbexchange)
[![Docker Repository](https://quay.io/repository/noteable/nbexchange/status "Docker Repository on Quay")](https://quay.io/repository/noteable/nbexchange)

A Jupyterhub service that replaces the nbgrader Exchange.

<!-- TOC -->

- [Highlights of nbexchange](#highlights-of-nbexchange)
  - [Compatibility](#compatibility)
- [What's in the code](#whats-in-the-code)
- [Documentation](#documentation)
  - [Database relationships](#database-relationships)
- [Installing](#installing)
  - [Helm Configuration](#helm-configuration)
- [Contributing](#contributing)
- [Configuration](#configuration)
  - [Configuring `nbexchange`](#configuring-nbexchange)
  - [Configuring `nbgrader`](#configuring-nbgrader)
  - [Releasing new versions](#releasing-new-versions)

<!-- /TOC -->

# Highlights of nbexchange

From [nbgrader](https://github.com/jupyter/nbgrader): _Assignments_ are `created`, `generated`, `released`, `fetched`, `submitted`, `collected`, `graded`. Then `feedback` can be `generated`, `released`, and `fetched`.

The exchange is responsible for recieving _release_/_fetch_ path, and _submit_/_collect_ cycle. It also allows _feedback_ to be transferred from instructor to student.

In doing this, the exchange is the authoritative place to get a list of what's what.

`nbexchange` is an external exchange plugin, designed to be run as a docker instance (probably inside a K8 cluster)

It's provides an external store for released & submitted assignments, and [soon] the feeback cycle.

Following the lead of other Jupyter services, it is a `tornado` application.
## Compatibility

This version is compatible with `nbgrader` >= 0.6.2

# What's in the code

This package contains three separate components:

- There's the actual nbexchange app, the component that handles the exchange of assignments.
  - It is, like much of the Jupyter ecosystem, a `tornado` application
  - `nbexchange/app.py` is the main class for the service
  - The handlers for the API calls all live in `nbexchange/handlers/`, and the authentication routine is in `nbexchange/handlers/auth/`
- There's a suite of plugins for `nbgrader`, in the appropriately named `nbexchange/plugin/`. If/As nbgrader changes, these need to be changed to match. These get installed in a jupyter notebook, but don't care about Classic vs Lab
- There's an additional extension for showing the _history_ of activity for a course / assignment. This is specific & unique to nbexchange.
  - It gets installed in a jupyter notebook, and needs enabled as normal.
  - It is only aware of the Classic interface, and does not work in the Lab UI.
  - The notebook server-side (python code) is in `nbexchange/server_extensions/`
  - The notebook client-side (javascript code) is in `nbexchange/nbextensions/nbexchange_history`

# Documentation

This exchange has some fundamental design decisions driven by the environment which drove its creation.

There are the following assumptions:

- You have an API for authenticating users who connect to the exchange (probably Jupyterhub, but not always)
- Usernames will be unique across the whole system
- Internal storage is in two parts:
  - An sql database for metadata, and
  - A filesystem for, well, files.
- There will always be a course_code
  - There may be multiple assignments under one course,
  - `assignment_code`s will be unique to a course
  - `assignment_code`s may be repeated in different `organisation_id`
- There will always be an `organisation_id`
  - `course_code`s must be uniqie within an `organisation_id`,
  - `course_code`s may be repeated in different `organisation_id`

All code should have `docstrings`.

Documentation currently in [docs/](docs/) - should be in readthedocs

## Database relationships

![Diagram of table relationships](table_relationships.png)

# Installing

Nbexchange can be installed as a Helm chart or as a pip dependency:


```
helm install --name nbexchange --namespace default ./chart -f myconfiguration.yaml
```

or

```
pip install .
```

## Helm Configuration

| Parameter  | Description    | Default |
| ---------- | -------------- | ------- |
| `replicaCount` | Replica count | 1  |
| `image.repository` | Image repository | `quay.io/noteable/nbexchange` |
| `image.tag` | Image tag | `latest` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `environment` | Environment variables for the application | `{}` |
| `service.type` | Type of Service | `ClusterIP` |
| `service.port` | Port to expose service under | `9000` |
| `resources.requests.cpu` | CPU resource requests | `200m` |
| `resources.requests.memory` | Memory resource requests | `256Mi` |
| `tolerations` | Pod taint tolerations for deployment| `[]` |
| `nodeSelector` | Pod node selector for deployment | `{}` |


# Contributing

See [Contributing.md](CONTRIBUTING.md)

# Configuration

There are two parts to configuring `nbexchange`:

- Configure `nbexchange` itself
- Configure `nbgrader` to use `nbexchange`

## Configuring `nbexchange`

The exchange uses `nbexchange_config.py` for configuration.

```python
from nbexchange.handlers.auth.user_handler import BaseUserHandler

class MyUserHandler(BaseUserHandler):

    def get_current_user(self, request):
        return {
          "name": "myname",
          "course_id": "cool_course_id",
          "course_title": "cool course",
          "course_role": "Student",
          "org_id": 1,
    }


c.NbExchange.user_plugin_class = MyUserHandler

c.NbExchange.base_url = /services/exchange
c.NbExchange.base_storage_location = /var/data/exchange/storage
c.NbExchange.db_url = mysql://username:password@my.msql.server.host:3306/db_name
```

- **`base_url`**

This is the _service_ url for jupyterhub, and defaults to `/services/nbexchange/`

Can also be defined in the environment variable `JUPYTERHUB_SERVICE_PREFIX`

- **`base_storage_location`**

This is where the exchange will store the files uploaded, and defaults to `/tmp/courses`

Can also be defined in the environment variable `NBEX_BASE_STORE`

- **`db_url`**

This is the database connector, and defaults to an in-memory SQLite (`sqlite:///:memory:`)

Can also be defined in the environment variable `NBEX_DB_URL`

- **`db_kwargs`** 

Where to include any kwargs to pass to the database connection.

- **`max_buffer_size`**

The service will limit the size of uploads. The figure is bytes

By default, upload sizes are limited to 5GB (5253530000)

- **`upgrade_db`**, **`reset_db`**, **`debug_db`**  

Do stuff to the db... see the code for what these do

- **`user_plugin_class`**

This is a class that defines how `get_current_user` works.

For the exchange to work, it needs some details about the user connecting to it - specifically, it needs 7 pieces of information:

- `name`: The username of the person (eg `perllaghu`),
- `full_name`: The optional full name, if supplied by the remote authenticator
- `course_id`: The course code as used in nbgrader (eg `cool_course`),
- `course_title`: A long name for the course (eg `A course of understanding thermondynamics in bulk refrigerant transport"),
- `course_role`: The role of the user, normally `Student` or `Instructor`. (currently only `Instructor` get privilaged actions),
- `org_id`: As mentioned above, nbexchange divides courses and users across organisations. This is an id (numeric) for the org_id for the user.
- `cust_id`: Whilst most of the exchange is keyed on the `org_id`, knowing _customer_ can be useful. This is an id (numeric) for the org_id for the user.

## Configuring `nbgrader`

The primary reference for this should be the `nbgrader` documentation - but in short:

1. Use the `nbgrader` code-base that supports the external exchange (nbgrader 0.7 and later)
2. Install the code from `nbexchange/plugin` into `nbgrader`
3. Include the following in your `nbgrader_config.py` file:

```python
## A plugin for collecting assignments.
c.ExchangeFactory.collect = 'nbexchange.plugin.ExchangeCollect'
## A plugin for exchange.
c.ExchangeFactory.exchange = 'nbexchange.plugin.Exchange'
## A plugin for fetching assignments.
c.ExchangeFactory.fetch_assignment = 'nbexchange.plugin.ExchangeFetchAssignment'
## A plugin for fetching feedback.
c.ExchangeFactory.fetch_feedback = 'nbexchange.plugin.ExchangeFetchFeedback'
## A plugin for listing exchange files.
c.ExchangeFactory.list = 'nbexchange.plugin.ExchangeList'
## A plugin for releasing assignments.
c.ExchangeFactory.release_assignment = 'nbexchange.plugin.ExchangeReleaseAssignment'
## A plugin for releasing feedback.
c.ExchangeFactory.release_feedback = 'nbexchange.plugin.ExchangeReleaseFeedback'
## A plugin for submitting assignments.
c.ExchangeFactory.submit = 'nbexchange.plugin.ExchangeSubmit'
```

These plugins will also check the size of _releases_ & _submissions_

`c.Exchange.max_buffer_size = 204800  # 200KB`

By default, upload sizes are limited to 5GB (5253530000)
The figure is bytes

## Releasing new versions

* Update `pyproject.toml` and `nbexchange/__init__.py` to change to the new version
* Create a new git tag doing `git tag -a vx.y.z` to match the version above
