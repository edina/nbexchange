API Specification for the NBExchange service
============================================

All URLs relative to `/services/nbexchange`

Assignments
----------

    .../assignments?course_id=$course_code

**GET**: returns list of assignments

Returns 

    {"success": True,
        "value": [{
            "assignment_id": "$assignment_code",
            "course_id": "$course_code",
            "student_id": Int
            "status": Str,
            "path": path,
            "notebooks": [
                { "notebook_id": x.name,
                  "has_exchange_feedback": False,
                  "feedback_updated": False,
                  "feedback_timestamp": None, } for x in assignment.notebooks],
            "timestamp": action.timestamp.strftime(
                "%Y-%m-%d %H:%M:%S.%f %Z"
            ),
        },
        {},..
        ]}
or

    {"success": False, "note": $note}


Assignment
----------

    .../assignment?course_id=$course_code&assignment_id=$assignment_code

**GET**: downloads assignment

Returns binary data or raises Exception (which is returned as a `503` error)
     
**POST**: (role=instructor, with file): Add ("release") an assignment
returns

    {"success": True, "note": "Released"}

or raises Exception (which is returned as a `503` error)

**DELETE**:  (role=instructor, with file): Remove an assignment.

Marks an asiignment as ``active: False``, and forgets any associated notebooks. Returns

    {"success": True, "note": "Assignment '$assignment_code' on course '$course_code' marked as unreleased by user $user" 

Takes as *optional* parameter ``purge``. This will delete the notebooks, the assignment,
and any associated data (``actions``, ``feedback``, etc). Returns

    {"success": True, "note": "Assignment '$assignment_code' on course '$course_code' deleted and purged from the database by user $user"}

If there are permission issues, returns

    {"success": False, "note": $note}

Submission
----------

    .../submission?course_id=$course_code&assignment_id=$assignment_code

**POST**: stores the submission for that user
returns

    {"success": True, "note": "Released"}

or raises Exception (which is returned as a `503` error)

Collections
-----------

    .../collections?course_id=$course_code&assignment_id=$assignment_code

**GET**: gets a list of submitted items
Return: same as `Assignments <#assignments>`

Collection
----------

    .../collections?course_id=$course_code&assignment_id=$assignment_code&path=$url_encoded_path

**GET**: downloads submitted assignment
Return: same as `Assignment <#assignment>`