# API Specification for the NBExchange service

## Usage

All URLs relative to `/services/nbexchange`

All responses will have the form
```json
{
    "data": "Mixed type holding the content of the response",
    "message": "Description of what happened"
}
```

### Assignments

`.../assignments/$course_code`

GET: returns a list of assignments available for that course
POST: creates a new course-code in the system

### Assignment

`.../assignment/$course_code/$assignment_code`

GET: Downloads that assignment
POST (with data): Add ("release") an assignment [Instructor only]


### Submissions

Submission calls:

`.../submissions/$course_code/$assignment_code/`

GET: gets list of users who've submitted so far

`.../submissions/$course_code/$assignment_code/$username`

GET: gets list is submissions for that user (may be more than 1!)

### Submission

`.../submission/$course_code/$assignment_code/$username`

GET: gets the assignment for that user [Instructor only]
POST (with data) stores the submission for that user

### Feedback

`.../feedback/$course_code/$assignment_code/$username`

GET: gets the feedback [instructors can see any relevant student, other their own only]
POST: uploads feedback [instructors only]

This relys on users being logged in, and the user-object having additional data:
`role` (as per LTI)

Also relies on
1) database having a list of user->course with role, and assignments for courses - and
2) calls to be able to query:
* `is user 'abc' associated with course 'xyz', and if so, what role?`
* `list of courses for user 'abc'`
* `list of users for course 'xyz'`
* `list of assignments for [user or course]`