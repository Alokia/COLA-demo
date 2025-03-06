from abc import ABC, abstractmethod
from typing import List, Dict


class BaseLM(ABC):
    @abstractmethod
    def query(self, messages: List[Dict[str, str]], **kwargs):
        pass
