[![coverage report](https://gitlab.edina.ac.uk/naas/nbexchange/badges/master/coverage.svg)](https://gitlab.edina.ac.uk/naas/nbexchange/commits/master)

# nbexchange

A Jupyterhub service that replaces the nbgrader Exchange.

[Service API specification](specification.md)

This is a minimal example of Jupyterhub running with one service

Facts:
- The dummy authenticator is used, which means every username/password combinations is accepted
- The sudospawner is used, so we can spawn a notebook for every user without the need for kubernetes
- In order for the sudospawner to work, the user needs to exist and have a home directory (you can add users in the docker build file)
- The service is a tornado app, heavily leverage example code from `nbgrader` and `hubshare`
- The service will be available (to logged in users) on `http://$HUB_URL/services/nbexchange`

The urls avaiable should be:

    http://$HUB_URL/services/nbexchange/user
    http://$HUB_URL/services/nbexchange/assignment/$COURSE_CODE
    http://$HUB_URL/services/nbexchange/assignment/$COURSE_CODE/$ASSIGNMENT?CODE

and POST requests to

    http://$HUB_URL/services/nbexchange/assignment/$COURSE_CODE/$ASSIGNMENT?CODE

(hoever that will only accept conenctions from users who are `instructors` on the given course)
