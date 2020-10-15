from datetime import datetime
from sqlalchemy import UniqueConstraint, Column, Integer, Unicode, ForeignKey, DateTime

from nbexchange.models import Base


class Feedback(Base):

    __tablename__ = "feedback_2"

    #: Unique id of the feedback (automatically incremented)
    id = Column(Integer(), primary_key=True, autoincrement=True)

    notebook = None
    #: Unique id of :attr:`~nbexchange.orm.Notebook.assignment`
    notebook_id = Column(
        Integer(), ForeignKey("notebook.id", ondelete="CASCADE"), index=True
    )

    instructor = None
    instructor_id = Column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True
    )

    student = None
    student_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True)

    location = Column(
        Unicode(200), nullable=True
    )  # Location for the file of this action
    checksum = Column(Unicode(200), nullable=True)  # Checksum for the feedback file
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    def __repr__(self):
        return f"Feedback<Notebook-{self.notebook_id}/Student-{self.student_id}/{self.checksum}>"
