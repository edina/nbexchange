# Changelog

## v2.0.5

* Update to Python 3.15
* Update to SQLAlchemy 2.1 (and thus psycopg v3)
* nbgrader itself is moved to a development dependency (it's only used in tests)
  
## v2.0.4

* Add validity-check when reading a file in 'collect' to stop out-of-bounds downloads
* Restrict SQLAlchemy to <2.1 to retain psycopg2-binary dependency
* Switch base Docker image from Bullseye to Trixie
* Tighten up on the active maintainers list

## v2.0.3

* Fix history API timeout issues with lazy-loading and pagination

## v2.0.2

* Fix broken default timestamps
* Handle timezones better
* Add course_id as a parameter to the history API
* Fix nbexchange liveness and readiness probes
* Ensure nbexchange handles passwords correctly

## v2.0.1

* (No changes recorded)

## v2.0.0

* Separate the jlab plugins into a separate repository
* Update to Python 3.13
* Update README.md and CONTRIBUTING.md files
* Update sentry-sdk to v2.44.0
* Update GitLab CI configuration

## V1.5.0

* Update to nbgrader 0.9.5
* Update to pythion 3.13
* Ensure feedback timestamps match submittion timestamp
* Move "get_current_user" to an external class
* Improve max-buffer (submitted file) size handling
* General improvement in test coverage

## V1.4.1

* add a history api [but no UI]

## v1.4.0

* Update to nbgrader 9
* Deliberately *not* update to python 3.12 [there are jupyter issues with 3.12]
* Remove the CodeCoverage actions

## v1.3.1

* Minor updates to github actions

## v1.3.0

* Update to nbgrader 8
* update to python 3.11
* Minor documentation updates

## v1.2.9

* Update to nbgrader that works in lab (0.7.0+)
* Update to python 3.10
* Add addtional tests

## v1.2.8

Support for multiple markers

## v1.2.7

* Add a file-size upload limit (defaults to 5GB)
* Add verification that 'release_assignment' and 'submit' actually store the received file
* Correct bug in full name handlers
* Fix library versions for dependencies

## v1.2.6

Strip forward slashes from usernames

## v1.2.1

Move from setup.py to pyproject.toml

## v1.2.0

Add full names to gradebook when available

## v1.1.0

Update the exchange & plugin to use a fixed timestamp

## v1.0.1

Fix timestamps

## v1.0.0

First release of nbexchange after open sourcing the code.
