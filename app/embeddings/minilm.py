from typing import List
from sentence_transformers import SentenceTransformer

class MiniLM:
    """
    This class provides an interface to generate embeddings for text using the
    'sentence-transformers/all-MiniLM-L6-v2' model.

    Attributes:
        model (SentenceTransformer): The loaded MiniLM sentence transformer model.
    """

    def __init__(self) -> None:
        self.model: SentenceTransformer = SentenceTransformer('./app/embeddings/models/minilm-l6-v2', device='cuda')

    def get_embeddings(self, text: str) -> List[float]:
        return self.model.encode([text])[0].tolist()