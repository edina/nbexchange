import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, Text, Unicode, UniqueConstraint

from nbexchange.models import Base


class GradeEventOutbox(Base):
    __tablename__ = "grade_event_outbox"
    __table_args__ = (UniqueConstraint("source_revision"),)

    event_id = Column(Unicode(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    schema_version = Column(Integer, nullable=False, default=1)
    org_id = Column(Integer, nullable=False, index=True)
    course_id = Column(Integer, nullable=False)
    course_code = Column(Unicode(200), nullable=False)
    assignment_id = Column(Integer, nullable=False)
    assignment_code = Column(Text, nullable=False)
    learner_id = Column(Integer, nullable=False)
    learner_name = Column(Unicode(200), nullable=False)
    source_revision = Column(Unicode(200), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    attempt_count = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_error = Column(Text, nullable=False, default="")

    def payload(self):
        return {
            "event_id": self.event_id,
            "schema_version": self.schema_version,
            "organisation_id": self.org_id,
            "course": {"id": self.course_id, "code": self.course_code},
            "assignment": {"id": self.assignment_id, "code": self.assignment_code},
            "learner": {"id": self.learner_id, "name": self.learner_name},
            "source_revision": self.source_revision,
            "occurred_at": self.occurred_at.isoformat(),
        }
