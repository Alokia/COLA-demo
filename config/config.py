from pathlib import Path
import yaml
from collections import defaultdict
import time
from typing import Dict, Union


class Config(defaultdict):
    _instance = None

    def __init__(self):
        super().__init__()

    @staticmethod
    def get_instance():
        if Config._instance is None:
            Config._instance = Config()
        return Config._instance

    def _update_api_key(self, data: Dict):
        for k, v in data.items():
            if isinstance(v, Dict):
                self._update_api_key(v)
            if k == "openai_api_key" and not v:
                data[k] = self["openai_api_key"]
            elif k == "openai_api_base" and not v:
                data[k] = self["openai_api_base"]

    def load_agent_config(self, config_path: Path):
        with config_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self["agent"] = data
        self._update_api_key(self["agent"])

    def load_yaml(self, yaml_path: Path):
        with yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.update(data)

        if self["session_id"]:
            self["log_folder"] = self["root_path"] / self["log_folder"] / self["session_id"]
        else:
            uuid = time.strftime('%Y-%m-%d-%H-%M-%S', time.localtime())
            self["log_folder"] = self["root_path"] / self["log_folder"] / uuid
            self["session_id"] = uuid

        self["log_folder"].mkdir(parents=True, exist_ok=True)

    def safe_check(self):
        assert self["interact_mode"] in ["proactive", "passive", "non-interactive"]


config = Config.get_instance()
config["root_path"] = Path(__file__).resolve().parents[1]
assert config["root_path"].name == "COLA-demo"

config.load_yaml(config["root_path"] / "config/config.yaml")
config.load_agent_config(config["root_path"] / "config/agent_config.yaml")
config.safe_check()
