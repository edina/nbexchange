from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Unicode
from sqlalchemy.orm import relationship

from nbexchange.models import Base
from nbexchange.models.notebooks import Notebook


class Feedback(Base):

    __tablename__ = "feedback_2"

    #: Unique id of the feedback (automatically incremented)
    id = Column(Integer(), primary_key=True, autoincrement=True)

    # notebook = None
    #: Unique id of :attr:`~nbexchange.orm.Notebook.assignment`
    notebook_id = Column(Integer(), ForeignKey("notebook.id", ondelete="CASCADE"), index=True)

    # instructor = None
    instructor_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True)

    # student = None
    student_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True)

    location = Column(Unicode(200), nullable=True)  # Location for the file of this action
    checksum = Column(Unicode(200), nullable=True)  # Checksum for the feedback file
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # relationships: a specific piece of feedback is for a specific notebook, for a specific
    # student and a specific instructor
    notebook = relationship("Notebook")
    instructor = relationship("User", foreign_keys=[instructor_id])
    student = relationship("User", foreign_keys=[student_id])

    def __repr__(self):
        return f"Feedback<Notebook-{self.notebook_id}/Student-{self.student_id}/{self.checksum}>"

    @classmethod
    def find_by_pk(cls, db, pk, log=None):
        """Find a feedback record by Primary Key.
        Returns None if not found.
        """
        if log:
            log.debug(f"Feedback.find_by_pk - pk:{pk}")

        if pk is None:
            raise ValueError("Primary Key needs to be defined")
        if isinstance(pk, int):
            return db.query(cls).filter(cls.id == pk).first()
        else:
            raise TypeError("Primary Keys are required to be Ints")

    @classmethod
    def find_notebook_for_student(cls, db, notebook_id, student_id, log=None, action=None):
        """Find the most recent piece of feedback for a given student/notebook combo

        feedback = orm.Feedback.find_notebook_for_student(
            db=session, notebook_id=current_notebook.id, student_id=some_user.id
        )

        Returns None if not found
        """
        if log:
            log.debug(f"Feedback.find_notebook_for_student - notebook_id:{notebook_id}, student_id:{student_id}")
        if notebook_id is None or not isinstance(notebook_id, int):
            raise TypeError("notebook_id must be defined, and an Int")
        if student_id is None or not isinstance(student_id, int):
            raise TypeError("notebook_id must be defined, and an Int")
        filters = [cls.notebook_id == notebook_id, cls.student_id == student_id]
        return db.query(cls).filter(*filters).order_by(cls.id.desc()).first()

    @classmethod
    def find_all_for_student(cls, db, student_id, assignment_id, log=None):
        """Find all the pieces of feedback for a student on an specified assignment

        results = orm.Feedback.find_all_for_notebook(
            db=session, assignment_id=current_assignment.id, student_id=some_user.id
        )

        Returns None if not found
        """
        if log:
            log.debug(f"Feedback.find_all_for_student - assignment_id:{assignment_id}, student_id:{student_id}")
        if assignment_id is None or not isinstance(assignment_id, int):
            raise TypeError("assignment_id must be defined, and an Int")
        if student_id is None or not isinstance(student_id, int):
            raise TypeError("notebook_id must be defined, and an Int")
        filters = [
            Notebook.assignment_id == assignment_id,
            cls.student_id == student_id,
        ]
        return db.query(cls).join(Notebook).filter(*filters).all()
