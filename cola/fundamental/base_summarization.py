from abc import ABC, abstractmethod


class BaseSummarization(ABC):
    @abstractmethod
    def summarize(self, **kwargs) -> str:
        """Summarize text."""
        pass
