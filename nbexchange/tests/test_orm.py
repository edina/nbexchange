"""Tests for the ORM bits"""
import pprint

import pytest
from sqlalchemy.exc import IntegrityError

# NOTE: All objects & relationships that are built up remain until the end of
# the test-run.
from nbexchange.models.actions import Action, AssignmentActions
from nbexchange.models.assignments import Assignment as AssignmentModel
from nbexchange.models.courses import Course
from nbexchange.models.notebooks import Notebook
from nbexchange.models.subscriptions import Subscription
from nbexchange.models.users import User

# from sqlite3 import IntegrityError


@pytest.fixture
def course_quirk(db):
    orm_thing = Course.find_by_code(db, code="quirk", org_id=2)
    if not orm_thing:
        orm_thing = Course(
            org_id=2, course_code="quirk", course_title="Spirit of the Age"
        )
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def course_strange(db):
    orm_thing = Course.find_by_code(db, code="Strange", org_id=1)
    if not orm_thing:
        orm_thing = Course(
            org_id=1, course_code="Strange", course_title="Damnation Alley"
        )
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def course_charm(db):
    orm_thing = Course.find_by_code(db, code="WEIRD", org_id=1)
    if not orm_thing:
        orm_thing = Course(
            org_id=1, course_code="WEIRD", course_title="Fable of a Failed Race"
        )
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
    orm_thing = User.find_by_name(db, "kaylee")
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


@pytest.fixture
def assignment_tree(db):
    orm_thing = AssignmentModel.find_by_code(db, "tree 1")
    if not orm_thing:
        orm_thing = AssignmentModel(assignment_code="tree 1")
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def assignment_false(db):
    orm_thing = AssignmentModel.find_by_code(db, "not used")
    if not orm_thing:
        orm_thing = AssignmentModel(assignment_code="not used", active=False)
        db.add(orm_thing)
        db.commit()
    return orm_thing


def assert_not_found(db, ORMType, id):
    """Assert that an item with a given id is not found"""
    assert db.query(ORMType).filter(ORMType.id == id).first() is None


# Need to put this in to clear the actions from other tests
def test_empty_db(db):
    db.query(Action).delete()


def test_db_not_first(db):
    with pytest.raises(TypeError):
        found_by_pk = User.find_by_pk("abd", db)
    with pytest.raises(TypeError):
        found_by_pk = Course.find_by_pk("abd", db)
    with pytest.raises(TypeError):
        found_by_pk = AssignmentModel.find_by_pk("abd", db)


def test_user(db, user_kaylee):
    assert user_kaylee.name == "kaylee"
    assert user_kaylee.org_id == 1

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
    found_by_name = User.find_by_name(db, "badger")
    assert found_by_name is None


@pytest.mark.skip
def test_multiple_users(db, user_kaylee, user_johaannes, user_fidel):
    users = User.find_by_org(db, 1)
    assert len(users) == 2
    users = User.find_by_org(db, 2)
    assert len(users) == 1
    users = User.find_by_org(db, 3)
    assert len(users) == 0


def test_user_params(db, user_kaylee):
    # confirm named arguments work even when reversed
    found_by_pk = User.find_by_pk(pk=user_kaylee.id, db=db)
    assert found_by_pk.id == user_kaylee.id

    # test for unbexpected param
    with pytest.raises(TypeError):
        found_by_pk = User.find_by_pk(primary_key=user_kaylee.id, db=db)
    with pytest.raises(TypeError):
        found_by_name = User.find_by_name(username=user_kaylee.name, db=db)
    with pytest.raises(TypeError):
        found_by_id = User.find_by_org(id=user_kaylee.org_id, db=db)


def test_course(db, course_strange):
    assert course_strange.course_code == "Strange"
    assert course_strange.course_title == "Damnation Alley"

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

    found_by_code = Course.find_by_code(
        db, course_strange.course_code, course_strange.org_id
    )
    assert found_by_code.course_code == course_strange.course_code

    # in real code, org_id is probably a string, so lets confirm that works
    found_by_code = Course.find_by_code(db, course_strange.course_code, "1")
    assert found_by_code.course_code == course_strange.course_code

    found_by_code = Course.find_by_code(db, "SANE", course_strange.org_id)
    assert found_by_code is None
    found_by_code = Course.find_by_code(
        db, course_strange.course_code, course_strange.org_id + 10
    )
    assert found_by_code is None


def test_course_params(db, course_strange):
    # confirm named arguments work even when reversed
    found_by_code = Course.find_by_code(
        org_id=course_strange.org_id, db=db, code=course_strange.course_code
    )
    assert found_by_code.course_code == course_strange.course_code

    # confirm that putting the positional values the wrong way round will [probably] fail
    with pytest.raises(ValueError):
        found_by_code = Course.find_by_code(
            db, course_strange.org_id, course_strange.course_code
        )

    # test for unbexpected param
    with pytest.raises(TypeError):
        found_by_pk = Course.find_by_pk(primary_key=course_strange.id, db=db)
    with pytest.raises(TypeError):
        found_by_code = Course.find_by_code(
            course_code=course_strange.course_code, org_id=course_strange.org_id, db=db
        )
    with pytest.raises(TypeError):
        found_by_code = Course.find_by_code(
            code=course_strange.course_code, id=course_strange.org_id, db=db
        )
    with pytest.raises(TypeError):
        found_by_org = Course.find_by_org(id=course_strange.org_id, db=db)


@pytest.mark.skip
def test_multiple_courses(db, course_quirk, course_strange, course_charm):
    courses = Course.find_by_org(db, 1)
    assert len(courses) == 2
    courses = Course.find_by_org(db, 2)
    assert len(courses) == 1
    courses = Course.find_by_org(db, 3)
    assert len(courses) == 0


def test_assignment(db, assignment_tree):
    assert assignment_tree.assignment_code == "tree 1"
    assert assignment_tree.course_id is None

    with pytest.raises(ValueError):
        found_by_pk = AssignmentModel.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = AssignmentModel.find_by_pk(db, "abc")

    found_by_pk = AssignmentModel.find_by_pk(db, assignment_tree.id)
    assert found_by_pk.id == assignment_tree.id
    found_by_pk = AssignmentModel.find_by_pk(db, assignment_tree.id + 10)
    assert found_by_pk is None

    with pytest.raises(TypeError):
        found_by_code = AssignmentModel.find_by_code(
            db, assignment_tree.assignment_code, "abc"
        )

    found_by_code = AssignmentModel.find_by_code(db, assignment_tree.assignment_code)
    assert found_by_code.assignment_code == assignment_tree.assignment_code
    found_by_code = AssignmentModel.find_by_code(db, "SANE")
    assert found_by_code is None


def test_assignment_linking(db, course_strange, assignment_tree):
    assignment_tree.course_id = course_strange.id
    assert course_strange.assignments[0].id == assignment_tree.id


def test_with_inactive_assignment(db, course_strange, assignment_false):
    assignment_false.course_id = course_strange.id
    assert course_strange.assignments[0].id == assignment_false.id


def test_subscription(db, course_strange, user_johaannes):
    # Setup user and course
    role = "Student"

    orm_subscription = Subscription(
        user_id=user_johaannes.id, course_id=course_strange.id, role=role
    )
    db.add(orm_subscription)
    db.commit()

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


def test_subscription_relationships(db, course_strange, user_johaannes):
    assert course_strange.subscribers[0].user.id == user_johaannes.id
    assert user_johaannes.courses[0].course.id == course_strange.id


def test_assignment_actions_enum(db):

    assert len(AssignmentActions.__members__) == 7
    assert "released" in AssignmentActions.__members__
    assert "fetched" in AssignmentActions.__members__
    assert "submitted" in AssignmentActions.__members__
    assert "removed" in AssignmentActions.__members__
    assert "collected" in AssignmentActions.__members__
    assert "feedback_released" in AssignmentActions.__members__
    assert "feedback_fetched" in AssignmentActions.__members__


def test_action_missing_action(db, course_strange, assignment_tree, user_johaannes):
    role = "instructor"
    release_file = "/some/random/path/to/a/file.tzg"

    orm_subscription = Subscription(
        user_id=user_johaannes.id, course_id=course_strange.id, role=role
    )
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


def test_action_invalid_action(db, assignment_tree, user_johaannes):

    # subscription set up earlier
    release_file = "/some/random/path/to/a/file.tzg"

    # unsupported action
    does_a = "foo"
    with pytest.raises(IntegrityError):
        action = Action(
            user_id=user_johaannes.id,
            assignment_id=assignment_tree.id,
            location=release_file,
            action=does_a,
        )
        db.add(action)
        db.commit()
    db.rollback()


def test_action_base_mathods_and_find_by_pk(db, assignment_tree, user_johaannes):

    # subscription set up earlier
    release_file = "/some/random/path/to/a/file.tzg"

    does_a = AssignmentActions.released
    orm_action = Action(
        user_id=user_johaannes.id,
        assignment_id=assignment_tree.id,
        action=does_a,
        location=release_file,
    )
    db.add(orm_action)
    db.commit()

    assert orm_action.action == AssignmentActions.released
    assert orm_action.user.name == user_johaannes.name
    assert orm_action.location == release_file

    with pytest.raises(ValueError):
        found_by_pk = Action.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = Action.find_by_pk(db, "abc")

    found_by_pk = Action.find_by_pk(db, orm_action.id)
    assert found_by_pk.id == orm_action.id
    found_by_pk = Action.find_by_pk(db, orm_action.id + 10)
    assert found_by_pk is None

    assert orm_action.action == AssignmentActions.released
    assert orm_action.user.name == user_johaannes.name
    assert orm_action.location == release_file

    with pytest.raises(ValueError):
        found_by_pk = Action.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = Action.find_by_pk(db, "abc")

    found_by_pk = Action.find_by_pk(db, orm_action.id)
    assert found_by_pk.id == orm_action.id
    found_by_pk = Action.find_by_pk(db, orm_action.id + 10)
    assert found_by_pk is None


def test_action_find_by_action(db):

    # subscription & action set up earlier
    with pytest.raises(TypeError):
        found_by_pk = Action.find_most_recent_action(db, None)
    with pytest.raises(TypeError):
        found_by_pk = Action.find_most_recent_action(db, "abc")
    with pytest.raises(TypeError):
        found_by_pk = Action.find_most_recent_action(db, 1, dict())
    foo = db.query(Action).all()
    pprint.pprint(foo)
    found_by_pk = Action.find_by_pk(db, 1)
    found_recent = Action.find_most_recent_action(
        db, found_by_pk.assignment_id, found_by_pk.action
    )
    assert found_recent.action == found_by_pk.action
    found_recent = Action.find_most_recent_action(
        db, found_by_pk.assignment_id, AssignmentActions.feedback_fetched
    )
    assert found_recent == None


def test_action_find_by_action_distinguish_actions(db, assignment_tree, user_johaannes):

    # subscription & action set up earlier
    release_file = "/some/random/path/to/a/file.tzg"

    # Add a fetched actione
    orm_action = Action(
        user_id=user_johaannes.id,
        assignment_id=assignment_tree.id,
        action=AssignmentActions.fetched,
        location=release_file,
    )
    db.add(orm_action)
    db.commit()

    found_by_pk = Action.find_by_pk(db, 1)

    # Without an action, we just get the last action
    found_recent = Action.find_most_recent_action(db, found_by_pk.assignment_id)
    assert found_recent.action == AssignmentActions.fetched

    # We can get different entries if we define the action
    found_recent_a = Action.find_most_recent_action(
        db, found_by_pk.assignment_id, AssignmentActions.fetched
    )
    assert found_recent_a.action == AssignmentActions.fetched

    found_recent_b = Action.find_most_recent_action(
        db, found_by_pk.assignment_id, AssignmentActions.released
    )
    assert found_recent_b.action == AssignmentActions.released

    assert found_recent_a.id != found_recent_b.id


def test_notebook_base_mathods_and_find_by_pk(db, assignment_tree):

    orm_notebook = Notebook(
        name="Test 1",
        assignment_id=assignment_tree.id,
    )
    db.add(orm_notebook)
    db.commit()

    assert orm_notebook.name == "Test 1"
    assert orm_notebook.assignment.assignment_code == assignment_tree.assignment_code

    with pytest.raises(ValueError):
        found_by_pk = Notebook.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = Notebook.find_by_pk(db, "abc")

    found_by_pk = Notebook.find_by_pk(db, orm_notebook.id)
    assert found_by_pk.id == orm_notebook.id
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
        found_by_name = Notebook.find_by_name(db, None)
    with pytest.raises(TypeError):
        found_by_name = Notebook.find_by_name(db, "abc")
    with pytest.raises(TypeError):
        found_by_name = Notebook.find_by_name(db, "abc", "foo")

    found_by_name = Notebook.find_by_name(db, "Exam 2", assignment_tree.id)
    assert found_by_name.id == orm_notebook.id
    found_by_name = Notebook.find_by_name(db, "Exam 3", assignment_tree.id)
    assert found_by_name is None
    found_by_name = Notebook.find_by_name(
        db, assignment_id=assignment_tree.id, name="Exam 2"
    )
    assert found_by_name.id == orm_notebook.id


def test_notebook_find_all(db, assignment_tree):

    # previous notebooks still in the db
    with pytest.raises(TypeError):
        found_by_name = Notebook.find_by_name(db, None)
    with pytest.raises(TypeError):
        found_by_name = Notebook.find_by_name(db, "abc")
    found_by_name = Notebook.find_all_for_assignment(db, assignment_tree.id)
    assert len(found_by_name) == 2
