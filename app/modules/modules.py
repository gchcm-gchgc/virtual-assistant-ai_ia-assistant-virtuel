from typing import Type, TypeVar
from .chatbot import ChatBot

T = TypeVar('T', bound='Modules')

class Modules:
    """
    This class ensures a single instance of the modules is created and reused throughout the application.

    Attributes:
        chatbot (ChatBot): An instance of the ChatBot module.
    """

    _instance: Type[T] | None = None

    def __new__(cls: Type[T]) -> T:
        if cls._instance is None:
            cls._instance = super(Modules, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        self.chatbot: ChatBot = ChatBot()

    @classmethod
    def get_instance(cls: Type[T]) -> T:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance