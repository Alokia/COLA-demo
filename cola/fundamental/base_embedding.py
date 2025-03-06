from abc import ABC, abstractmethod
from typing import List, Union, Any


class BaseEmbedding(ABC):
    @abstractmethod
    def embed_query(self, text: Union[str, Any]) -> List[float]:
        """Embed query text."""
        pass

    @abstractmethod
    def get_embedding_dim(self) -> int:
        pass
