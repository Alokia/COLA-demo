import json
from pathlib import Path
from typing import List, Union, Dict


def load_json(file_path: Union[str, Path]) -> Dict:
    """Load a JSON file from disk."""
    if isinstance(file_path, str):
        file_path = Path(file_path)

    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"File {file_path} not found!.")

    with file_path.open("r", encoding="utf8") as file:
        json_dict = json.load(file)

    return json_dict


def save_json(file_path: Union[str, Path], json_dict: Union[List, Dict], indent: int = -1) -> None:
    """Save a JSON file to disk."""
    if isinstance(file_path, str):
        file_path = Path(file_path)

    with file_path.open("w", encoding="utf8") as file:
        if indent == -1:
            json.dump(json_dict, file, ensure_ascii=False)
        else:
            json.dump(json_dict, file, ensure_ascii=False, indent=indent)


def check_json_format(json_string: str) -> bool:
    """Check if a string is a valid JSON."""
    try:
        json.loads(json_string)
    except json.JSONDecodeError:
        return False
    return True


def extract_json_from_response(text: str, symbol: str = "json") -> Dict:
    """Extract JSON from a string."""
    if "```" not in text:
        raise ValueError("json format error, missing ```")
    text = text.split("```")[1].strip()
    if symbol is not None:
        if text.startswith(symbol):
            text = text[len(symbol):].strip()
    try:
        res = json.loads(text)
    except json.JSONDecodeError:
        raise ValueError("json format error, unable to parse to json format.")
    return res
