from typing import Type, TypeVar
from .mongo import Mongo
from .postgres import Postgres

T = TypeVar('T', bound='Queries')

class Queries:
    """
    This class provides centralized access to MongoDB and PostgreSQL query interfaces.

    Attributes:
        mongo (Mongo): An instance of the MongoDB query interface.
        postgres (Postgres): An instance of the PostgreSQL query interface.
    """

    _instance: Type[T] | None = None

    def __new__(cls: Type[T]) -> T:
        if cls._instance is None:
            cls._instance = super(Queries, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        self.mongo: Mongo = Mongo()
        self.postgres: Postgres = Postgres()

    @classmethod
    def get_instance(cls: Type[T]) -> T:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance