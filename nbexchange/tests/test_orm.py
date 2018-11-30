"""Tests for the ORM bits"""

import pytest
from nbexchange import orm


def assert_not_found(db, ORMType, id):
    """Assert that an item with a given id is not found"""
    assert db.query(ORMType).filter(ORMType.id == id).first() is None


def test_user(db):
    orm_user = orm.User(name="kaylee", org_id=1)
    db.add(orm_user)
    db.commit()

    assert orm_user.name == "kaylee"
    assert orm_user.org_id == 1

    found_by_name = orm.User.find_by_name(db, "kaylee")
    assert found_by_name.name == orm_user.name
    found_by_name = orm.User.find_by_name(db, "badger")
    assert found_by_name is None


def test_course(db):
    # VARS
    org_id = 1
    course_code = "WEIRD"
    course_title = "Weird course"

    orm_course = orm.Course(
        org_id=org_id, course_code=course_code, course_title=course_title
    )
    db.add(orm_course)
    db.commit()

    assert orm_course.course_code == course_code
    assert orm_course.course_title == course_title


def test_subscription(db):
    # Setup user and course

    org_id = 1
    course_code = "WEIRD"
    course_title = "Weird course"
    user_name = "Johaannes"
    role = "Student"

    orm_user = orm.User(name=user_name, org_id=org_id)
    db.add(orm_user)
    db.commit()

    orm_course = orm.Course(
        org_id=org_id, course_code=course_code, course_title=course_title
    )
    db.add(orm_course)
    db.commit()

    orm_subscription = orm.Subscription(
        user_id=orm_user.id, course_id=orm_course.id, role=role
    )
    db.add(orm_subscription)
    db.commit()

    assert orm_subscription.course.course_title == course_title
    assert orm_subscription.role == role
