from .logs import Logs
from .vault import Vault
from typing import Type, TypeVar, Any

T = TypeVar('T', bound='Utils')

class Utils:
    """
    This class provides centralized access to utility functions and shared resources,
    such as the Vault for secret management.

    Attributes:
        vault (Vault): An instance of the Vault for managing secrets.
    """

    _instance: Type[T] | None = None

    def __new__(cls: Type[T]) -> T:
        if cls._instance is None:
            cls._instance = super(Utils, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        self.vault: Vault = Vault()
        self.logs: Logs = Logs()

    @classmethod
    def get_instance(cls: Type[T]) -> T:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
