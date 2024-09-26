from typing import Optional
from utils import Utils
from .mongo import Database as MongoDB
from .postgres import Database as PostgresDB

class Databases:
    """
    Manages MongoDB and PostgreSQL database connections, ensuring single instances throughout the application.

    Attributes:
        mongo (MongoDB): An instance of the MongoDB connection.
        postgres (PostgresDB): An instance of the PostgreSQL connection.
    """

    _instance: Optional['Databases'] = None

    def __new__(cls, utils: Utils) -> 'Databases':
        if cls._instance is None:
            cls._instance = super(Databases, cls).__new__(cls)
            cls._instance._initialize(utils=utils)
        return cls._instance

    def _initialize(self, utils: Utils) -> None:
        self.mongo = MongoDB(utils=utils)
        self.postgres = PostgresDB(utils=utils)

    @classmethod
    def get_instance(cls) -> 'Databases':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance