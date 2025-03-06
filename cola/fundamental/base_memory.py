from abc import ABC, abstractmethod
from typing import Any, List, Optional, Tuple, Union


class BaseMemory(ABC):
    @abstractmethod
    def add(self, **kwargs):
        pass

    @abstractmethod
    def similarity_search(
            self, **kwargs: Any
    ) -> List[Union[str, Any]]:
        """Return docs most similar to query."""

    @abstractmethod
    def delete(self, **kwargs):
        pass

    def get_all_memory(self):
        raise NotImplementedError("get_all_memory method is not implemented")

    def load_memory(self, **kwargs):
        raise NotImplementedError("load_memory method is not implemented")

    def save_memory(self, **kwargs):
        raise NotImplementedError("save_memory method is not implemented")
