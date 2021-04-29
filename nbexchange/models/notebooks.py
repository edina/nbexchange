from sqlalchemy import Column, ForeignKey, Integer, Unicode, UniqueConstraint

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
        return f"Notebook<{self.assignment.assignment_code}/{self.name}>"

    @classmethod
    def find_by_pk(cls, db, pk, log=None):
        """Find a notebook by Primary Key.
        Returns None if not found.
        """
        if log:
            log.debug(f"Notebook.find_by_pk - pk:{pk}")

        if pk is None:
            raise ValueError(f"Primary Key needs to be defined")
        if isinstance(pk, int):
            return db.query(cls).filter(cls.id == pk).first()
        else:
            raise TypeError(f"Primary Keys are required to be Ints")

    @classmethod
    def find_by_name(cls, db, name, assignment_id, log=None):
        """Finds a named notebook for a given assignment

        action = orm.Notebook.find_by_name(
            db=session, assignment_id=current_assignment.id, name='Some string'
        )

        Returns None if not found

        """
        if log:
            log.debug(
                f"Notebook.find_by_name - assignment_id:{assignment_id}, name:{name})"
            )
        if assignment_id is None or not isinstance(assignment_id, int):
            raise TypeError(f"assignment_id must be defined, and an Int")
        if name is None or not isinstance(name, str):
            raise TypeError(f"name must be defined, and a string")
        filters = [cls.assignment_id == assignment_id, cls.name == name]
        return db.query(cls).filter(*filters).first()
        # I think it should be this to be safe:
        # return db.query(cls).filter(*filters).order_by(cls.id.desc()).first()

    @classmethod
    def find_all_for_assignment(cls, db, assignment_id, log=None):
        """Finds all the notebooks for a given assignment

        action = orm.Notebook.find_by_name(
            db=session, assignment_id=current_assignment.id
        )

        Returns None if not found

        """
        if log:
            log.debug(
                f"Notebook.find_all_for_assignment - assignment_id:{assignment_id}"
            )
        if assignment_id is None or not isinstance(assignment_id, int):
            raise TypeError(f"assignment_id must be defined, and an Int")

        filters = [cls.assignment_id == assignment_id]
        return db.query(cls).filter(*filters).all()
        # I think it should be this to be safe:
        # return db.query(cls).filter(*filters).order_by(cls.id.desc()).first()
