from sqlalchemy import UniqueConstraint, Column, Integer, Unicode, ForeignKey

from nbexchange.models import Base


class Notebook(Base):

    __tablename__ = "notebook"
    __table_args__ = (UniqueConstraint("name", "assignment_id"),)

    #: Unique id of the notebook (automatically incremented)
    id = Column(Integer(), primary_key=True, autoincrement=True)

    #: Unique human-readable name for the notebook, such as "Problem 1". Note
    #: the uniqueness is only constrained within assignments (e.g. it is ok for
    #: two different assignments to both have notebooks called "Problem 1", but
    #: the same assignment cannot have two notebooks with the same name).
    name = Column(Unicode(128), nullable=False)

    assignment = None
    #: Unique id of :attr:`~nbexchange.orm.Notebook.assignment`
    assignment_id = Column(Integer(), ForeignKey("assignment.id"))

    def __repr__(self):
        return f"Notebook<{self.assignment.name}/{self.name}>"