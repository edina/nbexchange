A Jupyterhub service that replaces the nbgrader Exchange.

<!-- TOC -->

- [Highlights of nbexchange](#highlights-of-nbexchange)
- [Documentation](#documentation)
- [Installing](#installing)
- [Contributing](#contributing)
- [Configuration](#configuration)
    - [Configuring `nbexchange`](#configuring-nbexchange)
    - [Configuring `nbgrader`](#configuring-nbgrader)
- [Know To-Do stuff](#know-to-do-stuff)

<!-- /TOC -->

# Highlights of nbexchange

From [nbgrader](https://github.com/jupyter/nbgrader): _Assignments_ are `created`, `generated`, `released`, `fetched`, `submitted`, `collected`, `graded`. Then `feedback` can be `generated`, `released`, and `fetched`.

The exchange is responsible for recieving *released* assignments, allowing those assignments to be *fetched*, accepting *submissions*, and allowing those submissions to be *collected*. It also allows *feedback* to be transferred.

In doing this, the exchange is the authoritative place to get a list of what's what.

`nbexchange` is an external exchange plugin, designed to be run as a docker instance (probably inside a K8 cluster)

It's provides an external store for released & submitted assignments, and [soon] the feeback cycle

Following the lead of other Jupyter services, it is a `tornado` application.

# Documentation

This exchange has some fundamental design decisions driven by the environment which drove its creation.

There are the following assumptions:
* You have an  
* usernames will be unique across the whole system
* There will always be a course_code
    * There may be multiple assignments under one course
    * assignment_codes will be unique to a course
    * assignment_codes may be repeated in different `organisation_id`
* There will always be an `organisation_id`
    * course_codes must bhe uniqie within an `organisation_id`,
    * course_codes may be repeated in different `organisation_id`

All code should have `docstrings`

Documentation currently in [docs/](docs/) - should be in readthedocs

# Installing

The exchange is designed to be deployed as a docker instance - either directly on a server, or in a K8 cluster (which is where it was originally developed for)

It requires a plugin for `nbgrader` (code included)

# Contributing

See [Contributing.md](Contributing.md)

# Configuration

There are two parts to configuring `nbexchange`:

* Configure `nbexchange` itself
* Configure `nbgrader` to use `nbexchange`

## Configuring `nbexchange`

The exchange uses `nbexchange_config.py` for configuration.

There are only 3 important things to configure:

* **`base_url`**

This is the _service_ url for jupyterhub, and defaults to `/services/nbexchange/`

Can also be defined in the environment variable `JUPYTERHUB_SERVICE_PREFIX`

* **`base_storage_location`**

This is where the exchange will store the files uploaded, and defaults to `/tmp/courses`

Can also be defined in the environment variable `NBEX_BASE_STORE`

* **`db_url`**

This is the database connector, and defaults to an in-memory SQLite (`sqlite:///:memory:`)

Can also be defined in the environment variable `NBEX_DB_URL`

## Configuring `nbgrader`

The primary reference for this should be the `nbgrader` documentation - but in short:

1. Use the `nbgrader` code-base that supports the external exchange
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

# Know To-Do stuff

* ~~Get the initial code up~~
* Get a master-branch established
* Get proper install method for `nbgrader` external-exchange plugin
* Get a `handlers/auth/user_handler` to get details from jupyterhub (users, courses, and assignments should all be in the config file)
* Get travis? CI integration working
* Get an external sanity-check for the code
* Get docs to ReadTheDocs