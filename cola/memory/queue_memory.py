from cola.fundamental import BaseMemory
from typing import List, Dict, Union, Any
from cola.utils.json_utils import save_json, load_json
from pathlib import Path


class QueueMemory(BaseMemory):
    def __init__(self):
        self.memory = []

    def add(self, messages: Union[List[Dict], Dict], **kwargs):
        if isinstance(messages, Dict):
            self.memory.append(messages)
        elif isinstance(messages, List):
            self.memory.extend(messages)
        else:
            raise ValueError("messages should be a dict or a list of dict")

    def similarity_search(self, k: int | None = None, **kwargs) -> List[Union[str, Any]]:
        if k is None:
            return self.memory
        if (length := len(self.memory)) <= k:
            return self.memory
        return self.memory[length - k:]

    def delete(self, index: int):
        del self.memory[index]

    def get_all_memory(self):
        return self.memory

    def load_memory(self, path: Union[str, Path], file_name: str, **kwargs):
        self.memory = load_json(Path(path) / (file_name + ".json"))

    def save_memory(self, path: Union[str, Path], file_name: str, **kwargs):
        path = Path(path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        save_json(path / (file_name + ".json"), self.memory)

