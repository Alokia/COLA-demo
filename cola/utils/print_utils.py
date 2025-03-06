from typing import Dict, Optional, Type, Callable, Union, List, Any, get_args
from colorama import Fore, Style, init
from pydantic import BaseModel
import json

init()


def format_print_dict(data: Dict, return_str: bool = False) -> Optional[str]:
    n = len(data)
    res = "{"
    for k, v in data.items():
        res += f"\n    {k}: " + str(v)
        if (n := n - 1) != 0:
            res += ","
    res += "\n}"
    if return_str:
        return res
    print(res)


def print_with_color(text: str, color: str = "", end: str = "\n") -> None:
    color_mapping = {
        "red": Fore.RED,
        "green": Fore.GREEN,
        "yellow": Fore.YELLOW,
        "blue": Fore.BLUE,
        "magenta": Fore.MAGENTA,
        "cyan": Fore.CYAN,
        "white": Fore.WHITE,
        "black": Fore.BLACK,
    }

    selected_color = color_mapping.get(color.lower(), "")
    colored_text = selected_color + text + Style.RESET_ALL

    print(colored_text, end=end)


def format_pydantic_model(format_model: Optional[Type[BaseModel]] = None,
                          indent: int = 4, return_str: bool = True,
                          pattern: Callable = lambda x: x) -> Union[str, Dict]:
    if format_model is None:
        return ""
    desc = {}
    for field, info in format_model.model_fields.items():
        if type(info.annotation) is type(BaseModel):
            d = format_pydantic_model(info.annotation, return_str=False)
        elif type(info.annotation) is type(List[Any]):
            args = get_args(info.annotation)
            d = str(info.annotation) + ". " + info.description
            if not info.is_required():
                d += f" Default value is `{info.default}`."
            for arg in args:
                if type(arg) is type(BaseModel):
                    d = d + f". Type {arg} is defined as follows: " + format_pydantic_model(
                        arg, indent=0, return_str=True, pattern=lambda x: x.replace("\n", " "))
        else:
            d = str(info.annotation) + ". " + info.description
            if not info.is_required():
                d += f" Default value is `{info.default}`."
        desc[field] = d
    if return_str:
        desc = json.dumps(desc, indent=indent)
        desc = pattern(desc)
    return desc


def any_to_str(data: Any, indent: int = 4,
               first_line_indent: int = 0,
               last_line_indent: int = 0,
               pattern: Callable = lambda x: x) -> str:
    """Convert any data type to a string."""
    if isinstance(data, str):
        return data
    elif isinstance(data, (List, Dict)):
        try:
            str_data = json.dumps(data, ensure_ascii=False, indent=indent)
            str_data = str_data.split("\n")
            str_data[0] = " " * first_line_indent + str_data[0]
            str_data[-1] = " " * last_line_indent + str_data[-1]
            rstr = "\n".join(str_data)
            return pattern(rstr)
        except Exception:
            return str(data)
    else:
        return str(data)
