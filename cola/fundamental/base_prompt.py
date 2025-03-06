from abc import ABC, abstractmethod
from typing import Dict, List, Union, Optional, Type
from pathlib import Path
from PIL import Image
from cola.utils.image_utils import encode_pil_image_to_base64
from pydantic import BaseModel
from cola.utils.print_utils import format_pydantic_model, any_to_str
import yaml
from cola.utils.data_utils import PrivateData
from cola.utils.prompt_utils import catches


class BasePrompt(ABC):
    @staticmethod
    def create_role_prompt(role: str, contents: Union[List[Union[str, Image]], str], **kwargs) -> Dict:
        if isinstance(contents, str):
            return {"role": role, "content": contents}

        content = []
        for c in contents:
            if isinstance(c, str):
                if c.startswith("data:image"):
                    content.append({"type": "image_url", "image_url": {"url": c}})
                else:
                    content.append({"type": "text", "text": c})
            elif isinstance(c, (List, Dict)):
                content.append({"type": "text", "text": any_to_str(c)})
            elif isinstance(c, Image.Image):
                content.append({"type": "image_url",
                                "image_url": {"url": "data:image/jpeg;base64," + encode_pil_image_to_base64(c)}})
            else:
                raise ValueError(f"Invalid content type: {type(c)}")
        return {"role": role, "content": content}

    def create_ai_prompt(self, contents: Union[List[Union[str, Image]], str]) -> Dict:
        return self.create_role_prompt("assistant", contents)

    def create_user_prompt(self, contents: Union[List[Union[str, Image]], str]) -> Dict:
        return self.create_role_prompt("user", contents)

    @abstractmethod
    def create_system_prompt(self, *args, **kwargs) -> Dict[str, str]:
        pass

    @staticmethod
    def load_template(path: str | Path, **kwargs) -> str:
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"Prompt template not found at {path}")
        with path.open("r", encoding="utf-8") as f:
            template = f.read()
        return template

    @staticmethod
    def load_yaml(yaml_path: Path):
        with yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data

    @staticmethod
    def format_description(format_model: Optional[Type[BaseModel]] = None,
                           indent: int = 4, return_str: bool = True) -> Union[str, Dict]:
        return format_pydantic_model(format_model=format_model, indent=indent, return_str=return_str)

    @staticmethod
    def catch(data: PrivateData, param: str) -> List[str]:
        content = []
        if param in catches:
            content = catches[param](data)
        return content
