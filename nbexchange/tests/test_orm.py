"""Tests for the ORM bits"""

import pytest

import nbexchange.models.actions
import nbexchange.models.assignments
import nbexchange.models.courses
import nbexchange.models.subscriptions
import nbexchange.models.users

# convenience functions (ie, common to several tests)
# Note that they all test to see if they exist before they maken themselves
# (I know, we're using functionality before we've tested it..... )
#
# NOTE: All objects & relationships that are built up remain until the end of
# the test-run.
from nbexchange.models.actions import AssignmentActions


@pytest.fixture
def course_quirk(db):
    orm_thing = nbexchange.models.courses.Course.find_by_code(
        db, code="quirk", org_id=2
    )
    if not orm_thing:
        orm_thing = nbexchange.models.courses.Course(
            org_id=2, course_code="quirk", course_title="Spirit of the Age"
        )
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def course_strange(db):
    orm_thing = nbexchange.models.courses.Course.find_by_code(
        db, code="Strange", org_id=1
    )
    if not orm_thing:
        orm_thing = nbexchange.models.courses.Course(
            org_id=1, course_code="Strange", course_title="Damnation Alley"
        )
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def course_charm(db):
    orm_thing = nbexchange.models.courses.Course.find_by_code(
        db, code="WEIRD", org_id=1
    )
    if not orm_thing:
        orm_thing = nbexchange.models.courses.Course(
            org_id=1, course_code="WEIRD", course_title="Fable of a Failed Race"
        )
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def user_kaylee(db):
    orm_thing = nbexchange.models.users.User.find_by_name(db, "kaylee")
    if not orm_thing:
        orm_thing = nbexchange.models.users.User(name="kaylee", org_id=1)
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def user_johaannes(db):
    orm_thing = nbexchange.models.users.User.find_by_name(db, "kaylee")
    if not orm_thing:
        orm_thing = nbexchange.models.users.User(name="Johaannes", org_id=1)
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def user_fidel(db):
    orm_thing = nbexchange.models.users.User.find_by_name(db, "fidel")
    if not orm_thing:
        orm_thing = nbexchange.models.users.User(name="fidel", org_id=2)
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def assignment_tree(db):
    orm_thing = nbexchange.models.assignments.Assignment.find_by_code(db, "tree 1")
    if not orm_thing:
        orm_thing = nbexchange.models.assignments.Assignment(assignment_code="tree 1")
        db.add(orm_thing)
        db.commit()
    return orm_thing


@pytest.fixture
def assignment_false(db):
    orm_thing = nbexchange.models.assignments.Assignment.find_by_code(db, "not used")
    if not orm_thing:
        orm_thing = nbexchange.models.assignments.Assignment(
            assignment_code="not used", active=False
        )
        db.add(orm_thing)
        db.commit()
    return orm_thing


def assert_not_found(db, ORMType, id):
    """Assert that an item with a given id is not found"""
    assert db.query(ORMType).filter(ORMType.id == id).first() is None


def test_db_not_first(db):
    with pytest.raises(TypeError):
        found_by_pk = nbexchange.models.users.User.find_by_pk("abd", db)
    with pytest.raises(TypeError):
        found_by_pk = nbexchange.models.courses.Course.find_by_pk("abd", db)
    with pytest.raises(TypeError):
        found_by_pk = nbexchange.models.assignments.Assignment.find_by_pk("abd", db)


def test_user(db, user_kaylee):
    assert user_kaylee.name == "kaylee"
    assert user_kaylee.org_id == 1

    with pytest.raises(ValueError):
        found_by_pk = nbexchange.models.users.User.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = nbexchange.models.users.User.find_by_pk(db, "abc")

    found_by_pk = nbexchange.models.users.User.find_by_pk(db, user_kaylee.id)
    assert found_by_pk.id == user_kaylee.id
    found_by_pk = nbexchange.models.users.User.find_by_pk(db, user_kaylee.id + 10)
    assert found_by_pk is None

    with pytest.raises(ValueError):
        found_by_name = nbexchange.models.users.User.find_by_name(db, None)
    found_by_name = nbexchange.models.users.User.find_by_name(db, "kaylee")
    assert found_by_name.name == user_kaylee.name
    found_by_name = nbexchange.models.users.User.find_by_name(db, "badger")
    assert found_by_name is None


def test_multiple_users(db, user_kaylee, user_johaannes, user_fidel):
    users = nbexchange.models.users.User.find_by_org(db, 1)
    assert len(users) == 2
    users = nbexchange.models.users.User.find_by_org(db, 2)
    assert len(users) == 1
    users = nbexchange.models.users.User.find_by_org(db, 3)
    assert len(users) == 0


def test_user_params(db, user_kaylee):
    # confirm named arguments work even when reversed
    found_by_pk = nbexchange.models.users.User.find_by_pk(pk=user_kaylee.id, db=db)
    assert found_by_pk.id == user_kaylee.id

    # test for unbexpected param
    with pytest.raises(TypeError):
        found_by_pk = nbexchange.models.users.User.find_by_pk(
            primary_key=user_kaylee.id, db=db
        )
    with pytest.raises(TypeError):
        found_by_name = nbexchange.models.users.User.find_by_name(
            username=user_kaylee.name, db=db
        )
    with pytest.raises(TypeError):
        found_by_id = nbexchange.models.users.User.find_by_org(
            id=user_kaylee.org_id, db=db
        )


def test_course(db, course_strange):
    assert course_strange.course_code == "Strange"
    assert course_strange.course_title == "Damnation Alley"

    with pytest.raises(ValueError):
        found_by_pk = nbexchange.models.courses.Course.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = nbexchange.models.courses.Course.find_by_pk(db, "abc")

    found_by_pk = nbexchange.models.courses.Course.find_by_pk(db, course_strange.id)
    assert found_by_pk.id == course_strange.id
    found_by_pk = nbexchange.models.courses.Course.find_by_pk(
        db, course_strange.id + 10
    )
    assert found_by_pk is None

    with pytest.raises(TypeError):
        found_by_code = nbexchange.models.courses.Course.find_by_code(
            db, course_strange.course_code
        )

    with pytest.raises(ValueError):
        found_by_code = nbexchange.models.courses.Course.find_by_code(
            db, None, course_strange.org_id
        )
    with pytest.raises(ValueError):
        found_by_code = nbexchange.models.courses.Course.find_by_code(
            db, course_strange.course_code, None
        )

    found_by_code = nbexchange.models.courses.Course.find_by_code(
        db, course_strange.course_code, course_strange.org_id
    )
    assert found_by_code.course_code == course_strange.course_code

    # in real code, org_id is probably a string, so lets confirm that works
    found_by_code = nbexchange.models.courses.Course.find_by_code(
        db, course_strange.course_code, "1"
    )
    assert found_by_code.course_code == course_strange.course_code

    found_by_code = nbexchange.models.courses.Course.find_by_code(
        db, "SANE", course_strange.org_id
    )
    assert found_by_code is None
    found_by_code = nbexchange.models.courses.Course.find_by_code(
        db, course_strange.course_code, course_strange.org_id + 10
    )
    assert found_by_code is None


def test_course_params(db, course_strange):
    # confirm named arguments work even when reversed
    found_by_code = nbexchange.models.courses.Course.find_by_code(
        org_id=course_strange.org_id, db=db, code=course_strange.course_code
    )
    assert found_by_code.course_code == course_strange.course_code

    # confirm that putting the positional values the wrong way round will [probably] fail
    with pytest.raises(ValueError):
        found_by_code = nbexchange.models.courses.Course.find_by_code(
            db, course_strange.org_id, course_strange.course_code
        )

    # test for unbexpected param
    with pytest.raises(TypeError):
        found_by_pk = nbexchange.models.courses.Course.find_by_pk(
            primary_key=course_strange.id, db=db
        )
    with pytest.raises(TypeError):
        found_by_code = nbexchange.models.courses.Course.find_by_code(
            course_code=course_strange.course_code, org_id=course_strange.org_id, db=db
        )
    with pytest.raises(TypeError):
        found_by_code = nbexchange.models.courses.Course.find_by_code(
            code=course_strange.course_code, id=course_strange.org_id, db=db
        )
    with pytest.raises(TypeError):
        found_by_org = nbexchange.models.courses.Course.find_by_org(
            id=course_strange.org_id, db=db
        )


def test_multiple_courses(db, course_quirk, course_strange, course_charm):
    courses = nbexchange.models.courses.Course.find_by_org(db, 1)
    assert len(courses) == 2
    courses = nbexchange.models.courses.Course.find_by_org(db, 2)
    assert len(courses) == 1
    courses = nbexchange.models.courses.Course.find_by_org(db, 3)
    assert len(courses) == 0


def test_assignment(db, assignment_tree):
    assert assignment_tree.assignment_code == "tree 1"
    assert assignment_tree.course_id is None

    with pytest.raises(ValueError):
        found_by_pk = nbexchange.models.assignments.Assignment.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = nbexchange.models.assignments.Assignment.find_by_pk(db, "abc")

    found_by_pk = nbexchange.models.assignments.Assignment.find_by_pk(
        db, assignment_tree.id
    )
    assert found_by_pk.id == assignment_tree.id
    found_by_pk = nbexchange.models.assignments.Assignment.find_by_pk(
        db, assignment_tree.id + 10
    )
    assert found_by_pk is None

    with pytest.raises(TypeError):
        found_by_code = nbexchange.models.assignments.Assignment.find_by_code(
            db, assignment_tree.assignment_code, "abc"
        )

    found_by_code = nbexchange.models.assignments.Assignment.find_by_code(
        db, assignment_tree.assignment_code
    )
    assert found_by_code.assignment_code == assignment_tree.assignment_code
    found_by_code = nbexchange.models.assignments.Assignment.find_by_code(db, "SANE")
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

    orm_subscription = nbexchange.models.subscriptions.Subscription(
        user_id=user_johaannes.id, course_id=course_strange.id, role=role
    )
    db.add(orm_subscription)
    db.commit()

    with pytest.raises(ValueError):
        found_by_pk = nbexchange.models.subscriptions.Subscription.find_by_pk(db, None)
    with pytest.raises(TypeError):
        found_by_pk = nbexchange.models.subscriptions.Subscription.find_by_pk(db, "abc")

    found_by_pk = nbexchange.models.subscriptions.Subscription.find_by_pk(
        db, orm_subscription.id
    )
    assert found_by_pk.id == orm_subscription.id
    found_by_pk = nbexchange.models.subscriptions.Subscription.find_by_pk(
        db, orm_subscription.id + 10
    )
    assert found_by_pk is None

    assert orm_subscription.course.course_title == "Damnation Alley"
    assert orm_subscription.role == role


def test_subscription_relationships(db, course_strange, user_johaannes):
    assert course_strange.subscribers[0].user.id == user_johaannes.id
    assert user_johaannes.courses[0].course.id == course_strange.id


def test_action_release(db, course_strange, assignment_tree, user_johaannes):

    role = "instructor"
    release_file = "/some/random/path/to/a/file.tzg"

    orm_subscription = nbexchange.models.subscriptions.Subscription(
        user_id=user_johaannes.id, course_id=course_strange.id, role=role
    )
    db.add(orm_subscription)
    # assignment_tree.course_id = course_strange.id
    db.commit()

    # # unsupported action
    # does_a = "foo"
    # with pytest.raises(IntegrityError):
    #     action = orm.Action(
    #         user_id=user_johaannes.id,
    #         assignment_id=assignment_tree.id,
    #         action=does_a,
    #         location=release_file,
    #     )
    #     db.add(action)

    # proper action
    does_a = AssignmentActions.released
    action = nbexchange.models.actions.Action(
        user_id=user_johaannes.id,
        assignment_id=assignment_tree.id,
        action=does_a,
        location=release_file,
    )
    db.add(action)
    db.commit()

    assert action.action == AssignmentActions.released
    assert action.user.name == user_johaannes.name
    assert action.location == release_file


def test_assignment_actions_enum():

    assert "released" in AssignmentActions.__members__
    assert "fetched" in AssignmentActions.__members__
    assert "submitted" in AssignmentActions.__members__
    assert "removed" in AssignmentActions.__members__
