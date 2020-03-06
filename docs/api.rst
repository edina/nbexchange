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
or

    {"success": False, "note": $note}


Assignment
----------

    .../assignment?course_id=$course_code&assignment_id=$assignment_code

**GET**: downloads assignment

Returns binary data or raises Exception (which is returned as a `503` error
     
**POST**: (role=instructor, with file): Add ("release") an assignment
returns

    {"success": True, "note": "Released"}

or raises Exception (which is returned as a `503` error

Submission
----------

    .../submission?course_id=$course_code&assignment_id=$assignment_code

**POST**: stores the submission for that user
returns

    {"success": True, "note": "Released"}

or raises Exception (which is returned as a `503` error

Collections
-----------

    .../collections?course_id=$course_code&assignment_id=$assignment_code

**GET**: gets a list of submitted items
Return: same as [Assignments](#assignments)

Collection
----------

    .../collections?course_id=$course_code&assignment_id=$assignment_code&path=$url_encoded_path

**GET**: downloads submitted assignment
Return: same as [Assignment](#assignment)