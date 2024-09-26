import psycopg
import os
from utils import Utils
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker
from typing import Type, TypeVar
import logging

T = TypeVar('T', bound='Database')

class Database:
    """
    Manages PostgreSQL database connections using SQLAlchemy, ensuring a single instance throughout the application.

    Attributes:
        utils (Utils): Utility instance for accessing secrets.
        engine (Engine): SQLAlchemy engine for database connections.
        Session (sessionmaker): SQLAlchemy session factory.
        _initialized (bool): Flag indicating whether the instance has been initialized.
        _user (str): Database username.
        _pass (str): Database password.
        _host (str): Database host.
        _port (str): Database port.
        _dbname (str): Database name.
        _url_object (URL): SQLAlchemy URL object for database connection.
    """

    _instance = None

    def __new__(cls: Type[T], utils: Utils) -> T:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
            cls._instance.utils = utils
        return cls._instance

    def __init__(self, utils: Utils) -> None:
        if not self._initialized:
            self._initialize()

    def _initialize(self) -> None:
        try:
            self._set_db_conn_info()
            self._set_engine()
            self.Session = sessionmaker(bind=self.engine)
            self._initialized = True
        except Exception as e:
            print(f"Failed to connect to session attempting connection refresh: {e}")
            self._set_db_conn_info()
            self._set_engine()
            self.Session = sessionmaker(bind=self.engine)
            self._initialized = True

    @classmethod
    def __main__(cls: Type[T]) -> T:
        if cls._instance is None:
            raise ValueError("Database instance not initialized. Call Database(utils) first.")
        return cls._instance

    def get_psycopg_conn(self) -> psycopg.Connection:
        return psycopg.connect(
            conninfo=f"host={self._host} port={self._port} dbname={self._dbname} "
                     f"user={self._user} password={self._pass}",
            autocommit=True
        )
    
    def _set_db_conn_info(self) -> None:
        self._user = self.utils.vault.get_secret(os.environ['AZ_KEYVAULT_USER'])
        self._pass = self.utils.vault.get_secret(os.environ['AZ_KEYVAULT_PASS'])
        self._host = self.utils.vault.get_secret(os.environ['AZ_KEYVAULT_HOST'])
        self._port = self.utils.vault.get_secret(os.environ['AZ_KEYVAULT_PORT'])
        self._dbname = self.utils.vault.get_secret(os.environ['AZ_KEYVAULT_DBNAME'])
    
    def _set_engine(self) -> None:
        self._url_object = URL.create(
            drivername="postgresql+psycopg2",
            username=self._user,
            password=self._pass,
            host=self._host,
            database=self._dbname,
            port=self._port
        )
        self.engine = create_engine(
            self._url_object,
            isolation_level='AUTOCOMMIT',
            pool_size=int(os.environ['APP_CONN_POOL_SIZE']),
            max_overflow=int(os.environ['APP_MAX_OVERFLOW']),
            pool_pre_ping=True,
        )

    def log_connection(self) -> None:
        logging.info(self.engine.pool.status())

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None