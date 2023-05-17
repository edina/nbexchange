"""Tests for the ORM bits

These tests clear the database before starting, and then the
tests rely on information previously added.

The order of the model classes is roughly in the order that they'd
get used by the handlers:

User -> Course -> Subscription -> Assignment -> Action -> Notebook -> Feedback

"""
import pytest
from sqlalchemy.exc import IntegrityError

# NOTE: All objects & relationships that are built up remain until the end of
# the test-run.
from nbexchange.models.actions import Action, AssignmentActions
from nbexchange.models.assignments import Assignment as AssignmentModel
from nbexchange.models.courses import Course
from nbexchange.models.feedback import Feedback
from nbexchange.models.notebooks import Notebook
from nbexchange.models.subscriptions import Subscription
from nbexchange.models.users import User


@pytest.fixture
def course_quirk(db):
    orm_thing = Course.find_by_code(db, code="quirk", org_id=2)
    if not orm_thing:
        orm_thing = Course(org_id=2, course_code="quirk", course_title="Spirit of the Age")
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def course_strange(db):
    orm_thing = Course.find_by_code(db, code="Strange", org_id=1)
    if not orm_thing:
        orm_thing = Course(org_id=1, course_code="Strange", course_title="Damnation Alley")
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def course_charm(db):
    orm_thing = Course.find_by_code(db, code="WEIRD", org_id=1)
    if not orm_thing:
        orm_thing = Course(org_id=1, course_code="WEIRD", course_title="Fable of a Failed Race")
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def user_kaylee(db):
    orm_thing = User.find_by_name(db, "kaylee")
    if not orm_thing:
        orm_thing = User(name="kaylee", org_id=1)
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def user_johaannes(db):
    orm_thing = User.find_by_name(db, "Johaannes")
    if not orm_thing:
        orm_thing = User(name="Johaannes", org_id=1)
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def user_fidel(db):
    orm_thing = User.find_by_name(db, "fidel")
    if not orm_thing:
        orm_thing = User(name="fidel", org_id=2)
        db.add(orm_thing)
        db.commit()
    return orm_thing


# Rainbow Unicorn Rose (three "words")
@pytest.fixture
def user_rur(db):
    orm_thing = User.find_by_name(db, "🌈 🦄 🌹")
    if not orm_thing:
        orm_thing = User(name="🌈 🦄 🌹", org_id=2)
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def assignment_tree(db):
    orm_thing = AssignmentModel.find_by_code(db, "tree 1", 1)
    if not orm_thing:
        orm_thing = AssignmentModel(assignment_code="tree 1", course_id=1)
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def assignment_false(db):
    orm_thing = AssignmentModel.find_by_code(db=db, code="not used", course_id=1, active=False)
    if not orm_thing:
        orm_thing = AssignmentModel(assignment_code="not used", course_id=1, active=False)
        db.add(orm_thing)
        db.commit()
    return orm_thing


# Alpha to Omega via Infinity
@pytest.fixture
def assignment_a2ovi(db):
    orm_thing = AssignmentModel.find_by_code(db, "⍺ to ⍵ via ∞", 1)
    if not orm_thing:
        orm_thing = AssignmentModel(assignment_code="⍺ to ⍵ via ∞", course_id=1)
        db.add(orm_thing)
        db.commit()
    return orm_thing


# ## User tests


# Need to put this in to clear the database from the handler tests
def test_empty_db(db):
    db.query(Action).delete()
    db.query(AssignmentModel).delete()
    db.query(Course).delete()
    db.query(Feedback).delete()
    db.query(Notebook).delete()
    db.query(Subscription).delete()
    db.query(User).delete()


def test_user(db, user_kaylee):
    assert user_kaylee.name == "kaylee"
    assert user_kaylee.org_id == 1

    with pytest.raises(TypeError):
        found_by_pk = User.find_by_pk()
    with pytest.raises(ValueError):
        found_by_pk = User.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = User.find_by_pk(db, "abc")

    found_by_pk = User.find_by_pk(db, user_kaylee.id)
    assert found_by_pk.id == user_kaylee.id
    found_by_pk = User.find_by_pk(db, user_kaylee.id + 10)
    assert found_by_pk is None

    with pytest.raises(ValueError):
        found_by_name = User.find_by_name(db, None)
    found_by_name = User.find_by_name(db, "kaylee")
    assert found_by_name.name == user_kaylee.name
    assert str(found_by_name) == f"User/{found_by_name.name}"
    found_by_name = User.find_by_name(db, "badger")
    assert found_by_name is None


def test_user_find_by_org(db, user_johaannes, user_fidel):
    # uiser_kaylee already in db
    users = User.find_by_org(db, 1)
    assert len(users) == 2
    users = User.find_by_org(db, 2)
    assert len(users) == 1
    users = User.find_by_org(db, 3)
    assert len(users) == 0


def test_user_params(db, user_kaylee):
    # confirm named arguments work even when reversed
    # test for named parameters, and alternating positions
    found_1 = User.find_by_pk(db, user_kaylee.id)
    found_2 = User.find_by_pk(db=db, pk=user_kaylee.id)
    assert found_2.name == found_1.name
    found_3 = User.find_by_pk(pk=user_kaylee.id, db=db)
    assert found_3.name == found_1.name

    # test for unbexpected param
    with pytest.raises(TypeError):
        found_1 = User.find_by_pk(primary_key=user_kaylee.id, db=db)
    with pytest.raises(TypeError):
        found_1 = User.find_by_name(username=user_kaylee.name, db=db)
    with pytest.raises(TypeError):
        found_1 = User.find_by_org(id=user_kaylee.org_id, db=db)


# ## Course tests
# Remember Users are already in the DB


def test_course_basic_requirements(db, user_kaylee):
    orm_course = Course(
        org_id=user_kaylee.org_id,
        # course_code = "Strange",
    )
    db.add(orm_course)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    orm_course = Course(
        # org_id=user_kaylee.org_id,
        course_code="Strange",
    )
    db.add(orm_course)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    orm_course = Course(
        org_id=user_kaylee.org_id,
        course_code="Strange",
    )
    db.add(orm_course)
    db.commit()
    assert orm_course.course_code == "Strange"
    orm_course.course_title = "Damnation Alley"
    db.commit()


def test_course(db, course_strange):
    assert course_strange.course_code == "Strange"
    assert course_strange.course_title == "Damnation Alley"

    with pytest.raises(TypeError):
        found_by_pk = Course.find_by_pk()
    with pytest.raises(TypeError):
        found_by_pk = Course.find_by_pk(db)
    with pytest.raises(ValueError):
        found_by_pk = Course.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = Course.find_by_pk(db, "abc")

    found_by_pk = Course.find_by_pk(db, course_strange.id)
    assert found_by_pk.id == course_strange.id
    found_by_pk = Course.find_by_pk(db, course_strange.id + 10)
    assert found_by_pk is None

    with pytest.raises(TypeError):
        found_by_code = Course.find_by_code(db, course_strange.course_code)

    with pytest.raises(ValueError):
        found_by_code = Course.find_by_code(db, None, course_strange.org_id)
    with pytest.raises(ValueError):
        found_by_code = Course.find_by_code(db, course_strange.course_code, None)

    found_by_code = Course.find_by_code(db, course_strange.course_code, course_strange.org_id)
    assert found_by_code.course_code == course_strange.course_code
    assert str(found_by_code) == f"Course/{course_strange.course_code} {course_strange.course_title}"

    # in real code, org_id is probably a string, so lets confirm that works
    found_by_code = Course.find_by_code(db, course_strange.course_code, "1")
    assert found_by_code.course_code == course_strange.course_code

    found_by_code = Course.find_by_code(db, "SANE", course_strange.org_id)
    assert found_by_code is None
    found_by_code = Course.find_by_code(db, course_strange.course_code, course_strange.org_id + 10)
    assert found_by_code is None


def test_course_params(db, course_strange):
    # confirm named arguments work even when reversed
    found_by_code = Course.find_by_code(org_id=course_strange.org_id, db=db, code=course_strange.course_code)
    assert found_by_code.course_code == course_strange.course_code

    # confirm that putting the positional values the wrong way round will [probably] fail
    with pytest.raises(ValueError):
        found_by_code = Course.find_by_code(db, course_strange.org_id, course_strange.course_code)

    # test for unbexpected param
    with pytest.raises(TypeError):
        Course.find_by_pk(primary_key=course_strange.id, db=db)
    with pytest.raises(TypeError):
        found_by_code = Course.find_by_code(course_code=course_strange.course_code, org_id=course_strange.org_id, db=db)
    with pytest.raises(TypeError):
        found_by_code = Course.find_by_code(code=course_strange.course_code, id=course_strange.org_id, db=db)
    with pytest.raises(TypeError):
        Course.find_by_org(id=course_strange.org_id, db=db)


def test_multiple_courses(db, course_quirk, course_strange, course_charm):
    courses = Course.find_by_org(db, 1)
    assert len(courses) == 2
    courses = Course.find_by_org(db, 2)
    assert len(courses) == 1
    courses = Course.find_by_org(db, 3)
    assert len(courses) == 0


# ## Subscription tests
# Remember Users and Courses are already in the DB


def test_subscription(db, course_strange, user_johaannes):
    # Setup user and course
    role = "Student"
    orm_subscription = Subscription(
        user_id=user_johaannes.id,
        course_id=course_strange.id,
        # role=role
    )
    db.add(orm_subscription)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    orm_subscription = Subscription(role=role)
    db.add(orm_subscription)
    db.commit()
    # ## Why did that work??

    orm_subscription.user_id = user_johaannes.id
    orm_subscription.course_id = course_strange.id
    # orm_subscription = Subscription(
    #     user_id=user_johaannes.id, course_id=course_strange.id, role=role
    # )
    # db.add(orm_subscription)
    db.commit()

    with pytest.raises(TypeError):
        found_by_pk = Subscription.find_by_pk()
    with pytest.raises(TypeError):
        found_by_pk = Subscription.find_by_pk(db)
    with pytest.raises(ValueError):
        found_by_pk = Subscription.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = Subscription.find_by_pk(db, "abc")

    found_by_pk = Subscription.find_by_pk(db, orm_subscription.id)
    assert found_by_pk.id == orm_subscription.id
    found_by_pk = Subscription.find_by_pk(db, orm_subscription.id + 10)
    assert found_by_pk is None

    assert orm_subscription.course.course_title == "Damnation Alley"
    assert orm_subscription.role == role
    assert (
        str(orm_subscription) == f"Subscription for user {user_johaannes.id} to course {course_strange.id} as a {role}"
    )


def test_subscription_relationships(db, course_strange, user_johaannes):
    assert course_strange.subscribers[0].user.id == user_johaannes.id
    assert user_johaannes.courses[0].course.id == course_strange.id


def test_subscription_find_by_set(db, course_strange, user_johaannes):
    role = "Student"
    found_sub = Subscription.find_by_set(db, user_johaannes.id, course_strange.id, role)
    assert found_sub.user_id == user_johaannes.id
    assert found_sub.course_id == course_strange.id


# ## Assignment tests
# Remember Users, Courses, and Subscriptions are already in the DB


def test_assignment_actions_enum(db):
    assert len(AssignmentActions.__members__) == 7
    assert "released" in AssignmentActions.__members__
    assert "fetched" in AssignmentActions.__members__
    assert "submitted" in AssignmentActions.__members__
    assert "removed" in AssignmentActions.__members__
    assert "collected" in AssignmentActions.__members__
    assert "feedback_released" in AssignmentActions.__members__
    assert "feedback_fetched" in AssignmentActions.__members__


def test_assignment(db, course_strange):
    orm_assignment = AssignmentModel(
        # assignment_code="tree 1",
        course_id=course_strange.id,
    )
    db.add(orm_assignment)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    assignment_tree = AssignmentModel(
        assignment_code="tree 1",
        # course_id=course_strange.id,
    )
    db.add(assignment_tree)
    db.commit()
    assignment_tree.course_id = course_strange.id
    db.commit()

    with pytest.raises(TypeError):
        found_by_pk = AssignmentModel.find_by_pk()
    with pytest.raises(TypeError):
        found_by_pk = AssignmentModel.find_by_pk(db)
    with pytest.raises(ValueError):
        found_by_pk = AssignmentModel.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = AssignmentModel.find_by_pk(db, "abc")

    found_by_pk = AssignmentModel.find_by_pk(db, assignment_tree.id)
    assert found_by_pk.id == assignment_tree.id
    assert str(found_by_pk) == f"Assignment {assignment_tree.assignment_code} for course {assignment_tree.course_id}"

    found_by_pk = AssignmentModel.find_by_pk(db, assignment_tree.id + 10)
    assert found_by_pk is None

    with pytest.raises(ValueError):
        found_by_code = AssignmentModel.find_by_code(db, assignment_tree.assignment_code)
    with pytest.raises(TypeError):
        found_by_code = AssignmentModel.find_by_code(db, assignment_tree.assignment_code, "abc")
    with pytest.raises(TypeError):
        found_by_code = AssignmentModel.find_by_code(db, assignment_tree, assignment_tree.course_id)
    found_by_code = AssignmentModel.find_by_code(db, assignment_tree.assignment_code, assignment_tree.course_id)
    assert found_by_code.assignment_code == assignment_tree.assignment_code
    found_by_code = AssignmentModel.find_by_code(db, "SANE", assignment_tree.course_id)
    assert found_by_code is None


def test_assignment_linking(db, course_strange, assignment_tree):
    assignment_tree.course_id = course_strange.id
    assert course_strange.assignments[0].id == assignment_tree.id


def test_with_inactive_assignment(db, course_strange, assignment_false):
    assignment_false.course_id = course_strange.id
    assert course_strange.assignments[0].id == assignment_false.id


def test_assignment_find_for_course(db, course_strange, assignment_false, assignment_tree):
    courses = AssignmentModel.find_for_course(db, course_strange.id)
    assert len(courses.all()) == 1
    assignment_false.active = True
    courses = AssignmentModel.find_for_course(db, course_strange.id)
    assert len(courses.all()) == 2
    assignment_false.active = False


# ## Action tests
# Remember Users, Courses, Subscriptions, and Assignments are already in the DB


# a couple of "will not make" tests
def test_action_object_creation_errors(db, course_strange, assignment_tree, user_johaannes):
    role = "instructor"
    release_file = "/some/random/path/to/a/file.tzg"

    orm_subscription = Subscription(user_id=user_johaannes.id, course_id=course_strange.id, role=role)
    db.add(orm_subscription)
    db.commit()

    action = Action(
        user_id=user_johaannes.id,
        assignment_id=assignment_tree.id,
        location=release_file,
    )
    db.add(action)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # #### Why won't you work in github Actions, you bar steward
    # action = Action(
    #     user_id=user_johaannes.id,
    #     assignment_id=assignment_tree.id,
    #     location="/some/random/path/to/a/file.tzg",
    #     action="foo",
    # )
    # db.add(action)
    # with pytest.raises(Exception):
    #     db.commit()
    # db.rollback()

    orm_action = Action(
        action=AssignmentActions.released,
        location="/some/random/path/to/a/file.tzg",
    )
    # # Why does that work??

    db.add(orm_action)
    db.commit()
    orm_action.user_id = user_johaannes.id
    orm_action.assignment_id = assignment_tree.id
    db.commit()


def test_action_base_mathods_and_find_by_pk(db, assignment_tree, user_johaannes):
    # subscription set up earlier
    release_file = "/some/random/path/to/a/file.tzg"

    with pytest.raises(TypeError):
        found_by_pk = Action.find_by_pk()
    with pytest.raises(TypeError):
        found_by_pk = Action.find_by_pk(db)
    with pytest.raises(ValueError):
        found_by_pk = Action.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = Action.find_by_pk(db, "abc")

    found_by_pk = Action.find_by_pk(db, 1)
    assert found_by_pk.id == 1
    assert found_by_pk.action == AssignmentActions.released
    assert found_by_pk.location == release_file

    # check the relationships
    assert found_by_pk.user.name == user_johaannes.name
    assert found_by_pk.assignment.assignment_code == assignment_tree.assignment_code

    found_by_pk = Action.find_by_pk(db, 11)
    assert found_by_pk is None


def test_action_find_by_action(db):
    # subscription & action set up earlier
    with pytest.raises(TypeError):
        found_by_pk = Action.find_most_recent_action(db, None)
    with pytest.raises(TypeError):
        found_by_pk = Action.find_most_recent_action(db, "abc")
    with pytest.raises(TypeError):
        found_by_pk = Action.find_most_recent_action(db, 1, dict())

    found_by_pk = Action.find_by_pk(db, 1)  # released
    found_recent = Action.find_most_recent_action(db, found_by_pk.assignment_id, found_by_pk.action)
    assert found_recent.action == found_by_pk.action
    found_recent = Action.find_most_recent_action(db, found_by_pk.assignment_id, "released")
    assert found_recent.action == found_by_pk.action
    found_recent = Action.find_most_recent_action(db, found_by_pk.assignment_id, AssignmentActions.released)
    assert found_recent.action == found_by_pk.action
    found_recent = Action.find_most_recent_action(db, found_by_pk.assignment_id, AssignmentActions.feedback_fetched)
    assert found_recent is None


def test_action_find_by_action_distinguish_actions(db, assignment_tree, user_johaannes):
    # Add a fetched action
    orm_action = Action(
        user_id=user_johaannes.id,
        assignment_id=assignment_tree.id,
        action=AssignmentActions.fetched,
        location="/some/random/path/to/a/file.tzg",
    )
    db.add(orm_action)
    db.commit()

    found_by_pk = Action.find_by_pk(db, 1)

    # Without an action, we just get the last action
    found_recent = Action.find_most_recent_action(db, found_by_pk.assignment_id)
    assert found_recent.action == AssignmentActions.fetched

    # We can get different entries if we define the action
    found_recent_a = Action.find_most_recent_action(db, found_by_pk.assignment_id, AssignmentActions.fetched)
    assert found_recent_a.action == AssignmentActions.fetched

    found_recent_b = Action.find_most_recent_action(db, found_by_pk.assignment_id, AssignmentActions.released)
    assert found_recent_b.action == AssignmentActions.released

    assert found_recent_a.id != found_recent_b.id


def test_action_relationships(db, user_johaannes):
    found_by_pk = Action.find_by_pk(db, 1)
    assert found_by_pk.user.name == user_johaannes.name
    assert found_by_pk.assignment.assignment_code == "tree 1"
    assert found_by_pk.assignment.course.course_code == "Strange"


def test_action_can_restrict_assignment_searches(db, assignment_tree):
    found = AssignmentModel.find_by_code(db, assignment_tree.assignment_code, assignment_tree.course_id)
    assert found.id == assignment_tree.id
    found = AssignmentModel.find_by_code(
        db=db,
        code=assignment_tree.assignment_code,
        course_id=assignment_tree.course_id,
        action=AssignmentActions.released,
    )
    assert found.id == assignment_tree.id
    found = AssignmentModel.find_by_code(
        db=db,
        code=assignment_tree.assignment_code,
        course_id=assignment_tree.course_id,
        action=AssignmentActions.feedback_released,
    )
    assert found is None


# ## Notebook tests
# Remember Users, Courses, Subscriptions, Assignments, and Actions are already in the DB


def test_notebook_base_mathods_and_find_by_pk(db, assignment_tree):
    # name is required
    orm_notebook = Notebook(
        # name="Test 1",
        assignment_id=assignment_tree.id,
    )
    db.add(orm_notebook)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    orm_notebook = Notebook(
        name="Test 1",
        assignment_id=assignment_tree.id,
    )
    db.add(orm_notebook)
    db.commit()

    assert orm_notebook.name == "Test 1"
    assert orm_notebook.assignment.assignment_code == assignment_tree.assignment_code

    with pytest.raises(TypeError):
        found_by_pk = Notebook.find_by_pk()
    with pytest.raises(TypeError):
        found_by_pk = Notebook.find_by_pk(db)
    with pytest.raises(ValueError):
        found_by_pk = Notebook.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = Notebook.find_by_pk(db, "abc")

    found_by_pk = Notebook.find_by_pk(db, orm_notebook.id)
    assert found_by_pk.id == orm_notebook.id

    # # relationships
    assert found_by_pk.assignment.id == assignment_tree.id

    found_by_pk = Notebook.find_by_pk(db, orm_notebook.id + 10)
    assert found_by_pk is None


def test_notebook_find_by_name(db, assignment_tree):
    orm_notebook = Notebook(
        name="Exam 2",
        assignment_id=assignment_tree.id,
    )
    db.add(orm_notebook)
    db.commit()

    with pytest.raises(TypeError):
        found_by_name = Notebook.find_by_name()
    with pytest.raises(TypeError):
        found_by_name = Notebook.find_by_name(db)
    with pytest.raises(TypeError):
        found_by_name = Notebook.find_by_name(db, None)
    with pytest.raises(TypeError):
        found_by_name = Notebook.find_by_name(db, "abc")
    with pytest.raises(TypeError):
        found_by_name = Notebook.find_by_name(db, "abc", "foo")

    found_by_name = Notebook.find_by_name(db, "Exam 2", assignment_tree.id)
    assert found_by_name.id == orm_notebook.id
    found_by_name = Notebook.find_by_name(db, "Exam 3", assignment_tree.id)
    assert found_by_name is None
    found_by_name = Notebook.find_by_name(db, assignment_id=assignment_tree.id, name="Exam 2")
    assert found_by_name.id == orm_notebook.id


def test_notebook_find_all(db, assignment_tree):
    # previous notebooks still in the db
    with pytest.raises(TypeError):
        found_all_for_assignment = Notebook.find_all_for_assignment()
    with pytest.raises(TypeError):
        found_all_for_assignment = Notebook.find_all_for_assignment(db)
    with pytest.raises(TypeError):
        found_all_for_assignment = Notebook.find_all_for_assignment(db, None)
    with pytest.raises(TypeError):
        found_all_for_assignment = Notebook.find_all_for_assignment(db, "abc")
    found_all_for_assignment = Notebook.find_all_for_assignment(db, assignment_tree.id)
    assert len(found_all_for_assignment) == 2
    found_all_for_assignment = Notebook.find_all_for_assignment(assignment_id=assignment_tree.id, db=db)
    assert len(found_all_for_assignment) == 2


# kylee = instructor, johaanes = student
def test_feedback_base_mathods_and_find_by_pk(db, assignment_tree, user_kaylee, user_johaannes):
    # previous subscriptions & notebooks still in the db
    notebook = Notebook.find_by_name(db, "Exam 2", assignment_tree.id)
    released = Action.find_most_recent_action(db, assignment_tree.id, AssignmentActions.released)
    orm_feedback = Feedback(
        notebook_id=notebook.id,
        instructor_id=user_kaylee.id,
        student_id=user_johaannes.id,
        location=released.location,
        checksum="1234567890abcdef",
        timestamp=released.timestamp,
    )
    db.add(orm_feedback)
    db.commit()

    with pytest.raises(TypeError):
        found_by_pk = Feedback.find_by_pk()
    with pytest.raises(TypeError):
        found_by_pk = Feedback.find_by_pk(db)
    with pytest.raises(ValueError):
        found_by_pk = Feedback.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = Feedback.find_by_pk(db, "abc")

    found_by_pk = Feedback.find_by_pk(db, orm_feedback.id)
    assert found_by_pk.id == orm_feedback.id
    assert (
        str(found_by_pk)
        == f"Feedback<Notebook-{found_by_pk.notebook_id}/Student-{found_by_pk.student_id}/{found_by_pk.checksum}>"  # noqa: E501 W503
    )

    assert found_by_pk.notebook_id == notebook.id
    assert found_by_pk.instructor_id == user_kaylee.id
    assert found_by_pk.student_id == user_johaannes.id

    # relationships
    assert found_by_pk.notebook.name == notebook.name
    assert found_by_pk.instructor.name == user_kaylee.name
    assert found_by_pk.student.name == user_johaannes.name

    found_by_pk = Feedback.find_by_pk(db, orm_feedback.id + 10)
    assert found_by_pk is None


def test_feedback_find_notebook_for_student(db, assignment_tree, user_johaannes):
    # previous subscriptions, actions, feedback, and notebooks still in the db
    notebook = Notebook.find_by_name(db, "Exam 2", assignment_tree.id)

    with pytest.raises(TypeError):
        feedback = Feedback.find_notebook_for_student()
    with pytest.raises(TypeError):
        feedback = Feedback.find_notebook_for_student(db)
    with pytest.raises(TypeError):
        feedback = Feedback.find_notebook_for_student(db, "Exam 2")
    with pytest.raises(TypeError):
        feedback = Feedback.find_notebook_for_student(db, notebook.id, "Kaylee")

    feedback = Feedback.find_notebook_for_student(db, notebook.id, user_johaannes.id)
    assert feedback.notebook_id == notebook.id

    feedback = Feedback.find_notebook_for_student(db, student_id=user_johaannes.id, notebook_id=notebook.id)
    assert feedback.notebook_id == notebook.id


def test_feedback_find_all_for_student(db, assignment_tree, user_johaannes):
    # previous subscriptions, actions, feedback, and notebooks still in the db
    Notebook.find_by_name(db, "Exam 2", assignment_tree.id)

    with pytest.raises(TypeError):
        Feedback.find_all_for_student()
    with pytest.raises(TypeError):
        Feedback.find_all_for_student(db)
    with pytest.raises(TypeError):
        Feedback.find_all_for_student(db, "Johannes")
    with pytest.raises(TypeError):
        Feedback.find_all_for_student(db, user_johaannes.id, "tree 1")


def test_feedback_find_all_for_student_again(db, assignment_tree, user_johaannes, user_kaylee):
    notebook = Notebook.find_by_name(db, "Exam 2", assignment_tree.id)
    released = Action.find_most_recent_action(db, assignment_tree.id, AssignmentActions.fetched)
    orm_feedback = Feedback(
        notebook_id=notebook.id,
        instructor_id=user_kaylee.id,
        student_id=user_johaannes.id,
        location=released.location,
        checksum="234567890abcdef1",
        timestamp=released.timestamp,
    )
    db.add(orm_feedback)
    db.commit()

    # Note this this swaps instructor & user, so should *not* be included
    orm_feedback_2 = Feedback(
        notebook_id=notebook.id,
        instructor_id=user_johaannes.id,
        student_id=user_kaylee.id,
        location=released.location,
        checksum="34567890abcdef12",
        timestamp=released.timestamp,
    )
    db.add(orm_feedback_2)
    db.commit()

    feedback = Feedback.find_all_for_student(db, user_johaannes.id, assignment_tree.id)

    assert len(feedback) == 2


def test_all_the_unicode(db, assignment_a2ovi, user_rur, course_strange):
    # subscribe user to course
    # add assignment to course

    role = "instructor"
    release_file = "/some/random/path/to/a/file.tzg"
    orm_subscription = Subscription(user_id=user_rur.id, course_id=course_strange.id, role=role)
    db.add(orm_subscription)
    assignment_a2ovi.course_id = course_strange.id
    db.commit()

    found_by_pk = Subscription.find_by_pk(db, orm_subscription.id)
    assert found_by_pk.id == orm_subscription.id
    assert orm_subscription.course.course_title == "Damnation Alley"

    # release
    orm_action = Action(
        action=AssignmentActions.released,
        location=release_file,
    )
    db.add(orm_action)
    db.commit()
    orm_action.user_id = user_rur.id
    orm_action.assignment_id = assignment_a2ovi.id
    db.commit()

    # fetch
    orm_action = Action(
        user_id=user_rur.id,
        assignment_id=assignment_a2ovi.id,
        action=AssignmentActions.fetched,
        location=release_file,
    )
    db.add(orm_action)
    db.commit()

    found = Action.find_most_recent_action(db, assignment_a2ovi.id)
    assert found.user.name == user_rur.name
