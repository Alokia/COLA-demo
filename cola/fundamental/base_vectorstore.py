from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union, Tuple
from pathlib import Path


class BaseVectorStore(ABC):
    @abstractmethod
    def add_embeddings(
            self,
            keys: List[str],
            embeddings: List[List[float]] = None,
            **kwargs: Any,
    ) -> None:
        """Add embeddings to the vectorstore.

        Args:
            keys: list of metadatas associated with the embedding.
            embeddings: List of embeddings to add to the vectorstore.
            kwargs: vectorstore specific parameters

        Returns:
            List of ids from adding the texts into the vectorstore.
        """

    def delete(self, keys: Optional[List[str]] = None, **kwargs: Any) -> Optional[bool]:
        """Delete by vector ID or other criteria.

        Args:
            keys: List of ids to delete.
            **kwargs: Other keyword arguments that subclasses might use.

        Returns:
            Optional[bool]: True if deletion is successful,
            False otherwise, None if not implemented.
        """

        raise NotImplementedError("delete method must be implemented by subclass.")

    @abstractmethod
    def similarity_search(
            self, embedding: List[float], k: int = 4, score_threshold: Optional[float] = None, **kwargs: Any
    ) -> List[Tuple[str, float]]:
        """Return docs most similar to query."""

    def __contains__(self, item):
        raise NotImplementedError("__contains__ method must be implemented by subclass.")

    @abstractmethod
    def save_vectorstore(self, path: Union[str, Path], file_name: str) -> None:
        """Save vectorstore to disk."""

    @classmethod
    def load_vectorstore(cls, path: Union[str, Path], file_name: str) -> "BaseVectorStore":
        """load vectorstore from disk."""
