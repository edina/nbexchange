"""Change feedback timestamp column type to DateTime
Revision ID: 2805bf7747e5
Revises: f26d6a79159d
Create Date: 2020-06-23 13:58:38.781382
"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy import orm

# revision identifiers, used by Alembic.
from sqlalchemy.engine.reflection import Inspector

revision = "2805bf7747e5"
down_revision = "f26d6a79159d"
branch_labels = None
depends_on = None

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Unicode

from nbexchange.models import Base


def try_convert(datestr, default):
    try:
        return datetime.fromisoformat(datestr)
    except:
        try:
            return datetime.strptime(datestr, "%Y-%m-%d %H:%M:%S.%f %Z")
        except:
            try:
                return datetime.strptime(datestr, "%Y-%m-%d %H:%M:%S.%f").isoformat()
            except:
                return default


def upgrade():
    from nbexchange.models import Feedback as FeedbackNew

    class FeedbackOld(Base):
        __tablename__ = "feedback"
        id = Column(Integer(), primary_key=True, autoincrement=True)
        notebook = None
        notebook_id = Column(
            Integer(), ForeignKey("notebook.id", ondelete="CASCADE"), index=True
        )
        instructor = None
        instructor_id = Column(
            Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True
        )
        student = None
        student_id = Column(
            Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True
        )
        location = Column(
            Unicode(200), nullable=True
        )  # Location for the file of this action
        checksum = Column(Unicode(200), nullable=True)  # Checksum for the feedback file
        timestamp = Column(Unicode(12), nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow)

    bind = op.get_bind()

    inspector = Inspector.from_engine(bind)

    tables = inspector.get_table_names()

    if "feedback_2" not in tables:
        FeedbackNew.__table__.create(bind)

    session = orm.Session(bind=bind)

    if "feedback" in tables:
        feedbacks = [
            FeedbackNew(
                notebook_id=feedback.notebook_id,
                instructor_id=feedback.instructor_id,
                student_id=feedback.student_id,
                location=feedback.location,
                checksum=feedback.checksum,
                timestamp=try_convert(feedback.timestamp, feedback.created_at),
                created_at=feedback.created_at,
            )
            for feedback in session.query(FeedbackOld)
        ]
        session.add_all(feedbacks)

        session.commit()


def downgrade():
    from nbexchange.models import Feedback as FeedbackOld

    class FeedbackNew(Base):
        __tablename__ = "feedback_2"
        id = Column(Integer(), primary_key=True, autoincrement=True)
        notebook = None
        notebook_id = Column(
            Integer(), ForeignKey("notebook.id", ondelete="CASCADE"), index=True
        )
        instructor = None
        instructor_id = Column(
            Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True
        )
        student = None
        student_id = Column(
            Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True
        )
        location = Column(Unicode(200), nullable=True)
        checksum = Column(Unicode(200), nullable=True)  # Checksum for the feedback file
        timestamp = Column(DateTime(timezone=True), nullable=False)
        created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    bind = op.get_bind()
    session = orm.Session(bind=bind)
    inspector = Inspector.from_engine(bind)

    tables = inspector.get_table_names()
    if "feedback" not in tables:
        FeedbackOld.__table__.create(bind)

    if "feedback_2" in tables:
        feedbacks = [
            FeedbackOld(
                notebook_id=feedback.notebook_id,
                instructor_id=feedback.instructor_id,
                student_id=feedback.student_id,
                location=feedback.location,
                checksum=feedback.checksum,
                timestamp=feedback.timestamp.isoformat(),
                created_at=feedback.created_at,
            )
            for feedback in session.query(FeedbackNew)
        ]
        session.add_all(feedbacks)

        session.commit()
