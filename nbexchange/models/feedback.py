from datetime import datetime
from sqlalchemy import UniqueConstraint, Column, Integer, Unicode, ForeignKey, DateTime

from nbexchange.models import Base


class Feedback(Base):

    __tablename__ = "feedback"

    #: Unique id of the feedback (automatically incremented)
    id = Column(Integer(), primary_key=True, autoincrement=True)

    notebook = None
    #: Unique id of :attr:`~nbexchange.orm.Notebook.assignment`
    notebook_id = Column(Integer(), ForeignKey("notebook.id"))
    user = None
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True)
    location = Column(
        Unicode(200), nullable=True
    )  # Loction for the file of this action
    checksum = Column(
        Unicode(200), nullable=True
    )  # Checksum for the feedback file
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Feedback<Notebook-{self.notebook.id}/User-{self.user.id}/{self.checksum}>"
