from pathlib import Path
import json
from typing import Dict, List, Union
from cola.utils.image_utils import save_image
from config.config import Config

config = Config.get_instance()


class ChatMessageLogger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.log_folder = config["log_folder"]
        self.n_data = 1
        self.n_query = 1
        self.last_md_path: Path = Path(self.log_folder)
        self.role_last_md_path: Dict = dict()
        self._role = None

    @staticmethod
    def replace_image_base64_with_url(messages: List[Dict[str, Union[str, List[Dict]]]],
                                      folder: Path,
                                      second_folder: str,
                                      prefix: str = "",
                                      suffix: str = "png") -> List[Dict[str, Union[str, List[Dict]]]]:
        if second_folder:
            folder = folder / second_folder
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)

        n = 1
        new_messages = []
        for msg in messages:
            role, content = msg["role"], msg["content"]
            if isinstance(content, str):
                new_messages.append(dict(role=role, content=content))
            else:
                new_content = []
                for c in content:
                    if c["type"] == "image_url":
                        img_path = (folder / (prefix + f"{n}.{suffix}")).absolute()
                        new_content.append(dict(
                            type="image_url",
                            image_url={"url": "../" + second_folder + "/" + f"{n}.{suffix}"}
                        ))
                        save_image(c["image_url"]["url"], img_path)
                        n += 1
                    else:
                        new_content.append(dict(type=c["type"], text=c["text"]))
                new_messages.append(dict(role=role, content=new_content))
        return new_messages

    def log_markdown_chat_message(self, chat_messages: List[Dict[str, Union[str, List[Dict]]]],
                                  folder: Path, file_name: str):
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)

        self.last_md_path = folder / f"{file_name}.md"
        self.role_last_md_path[self._role] = self.last_md_path

        with (folder / f"{file_name}.md").open("w", encoding="utf-8") as f:
            for msg in chat_messages:
                f.write("# " + msg["role"] + "\n")
                if isinstance(msg["content"], str):
                    f.write(msg["content"] + "\n\n")
                else:
                    for c in msg["content"]:
                        if c["type"] == "text":
                            f.write(c["text"] + "\n\n")
                        else:
                            f.write("![]({})".format(c["image_url"]["url"]) + "\n\n")

    @staticmethod
    def log_json_chat_message(chat_messages: List[Dict[str, Union[str, List[Dict]]]],
                              folder: Path, file_name: str):
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
        with (folder / f"{file_name}.json").open("w", encoding="utf-8") as f:
            json.dump(chat_messages, f, indent=4)

    def log_data(self, data: Dict, folder: str, file_name: str = None):
        folder = self.log_folder if folder is None else self.log_folder / folder
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)

        if file_name is None:
            sender = str(data["sender"]).split(".")[-1]
            receiver = str(data["receiver"]).split(".")[-1]
            file_name = f"Step {self.n_data}" + " - " + sender + " - " + receiver
            self.n_data += 1

        new_data = {}
        for k, v in data.items():
            new_data[k] = str(v)
        with (folder / f"{file_name}.json").open("w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=4)

    def log(self, chat_messages: List[Dict[str, Union[str, List[Dict]]]],
            folder: Union[Path, str] = None, file_name: str = None, role: str = None):
        folder = self.log_folder if folder is None else self.log_folder / folder
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)

        if file_name is None:
            file_name = f"Query {self.n_query}"
            self.n_query += 1
            if role is not None:
                file_name += " - " + role
                self._role = role

        messages = self.replace_image_base64_with_url(chat_messages, folder, "images/" + file_name)
        self.log_json_chat_message(messages, folder / "json", file_name)
        self.log_markdown_chat_message(messages, folder / "markdown", file_name)
