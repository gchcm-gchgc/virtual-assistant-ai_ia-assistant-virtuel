from typing import Type, TypeVar
from .minilm import MiniLM
from .mpnet import MPNet

T = TypeVar('T', bound='Embeddings')

class Embeddings:
    """
    Singleton class for managing text embeddings using MiniLM.

    This class ensures a single instance of the MiniLM model is created and reused.

    Attributes:
        miniLM (MiniLM): An instance of the MiniLM model for generating embeddings.
    """

    _instance: Type[T] | None = None

    def __new__(cls: Type[T]) -> T:
        if cls._instance is None:
            cls._instance = super(Embeddings, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        self.minilm = MiniLM()
        self.mpnet = MPNet()

    @classmethod
    def get_instance(cls: Type[T]) -> T:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance