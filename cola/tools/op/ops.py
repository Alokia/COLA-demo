from pywinauto.controls.uiawrapper import UIAWrapper
from cola.tools.op.op_utils import OperationRegister
from pydantic import BaseModel, Field
import time
from cola.utils.datatype import RoleType
from cola.tools.op.special_operations import op_open_application
from typing import Any, Optional, List, Callable, Union, Dict
from cola.tools.controller.inspector import WindowsApplicationInspector
from config.config import Config
import pyautogui
import pandas as pd
from pathlib import Path
import json
from docx import Document
from PIL import Image, ImageOps

wai = WindowsApplicationInspector()
config = Config.get_instance()


class OpClickInputModel(BaseModel):
    button: str = Field(
        ...,
        description="""the button to click, can be "left", "right", "middle"."""
    )
    double: bool = Field(
        ...,
        description="""whether to double-click the control."""
    )


@OperationRegister(
    model=OpClickInputModel,
    roles=[RoleType.Searcher, RoleType.FileManager]
)
def click_input(window: UIAWrapper, control: UIAWrapper, button: str = "left", double: bool = False) -> None:
    """Click the control with the given button and double-click if needed.
Parameter:
[Parameter]
Notice:
    This function works with all type of controls.
Examples:
    1. {"func_name": "click_input", "params": {"button": "left", "double": True}}: This command will simulate double-click the left button.
    2. {"func_name": "click_input", "params": {"button": "right", "double": False}}: This command will simulate single-click the right button .
    """
    control.set_focus()
    time.sleep(0.5)
    control.click_input(button=button, double=double)
    return None


class OpKeyboardInputModel(BaseModel):
    keys: str = Field(
        ...,
        description="""It can be any key on the keyboard, with special keys represented by their virtual key codes. For example, "{VK_CONTROL}c" represents the Ctrl+C shortcut key.
here are some common virtual key codes: Shift - VK_SHIFT, Ctrl - VK_CONTROL, Alt - VK_MENU, Enter - VK_RETURN, Space - VK_SPACE, Tab - VK_TAB, Esc - ESC, Backspace - BACKSPACE, Delete - DELETE, Up - VK_UP, Down - VK_DOWN, Left - VK_LEFT, Right - VK_RIGHT, F1 - VK_F1, F2 - VK_F2, F3 - VK_F3, F4 - VK_F4, F5 - VK_F5, F6 - VK_F6, F7 - VK_F7, F8 - VK_F8, F9 - VK_F9, F10 - VK_F10, F11 - VK_F11, F12 - VK_F12, etc."""
    )
    clear: bool = Field(
        ...,
        description="""Whether to clear the existing text in the control item before inputting the new text."""
    )
    click_enter: bool = Field(
        ...,
        description="""Whether to press the Enter button after typing the text. 
With the exception of recording text, opening applications, etc., almost all other actions require pressing Enter to get new content."""
    )


@OperationRegister(
    model=OpKeyboardInputModel,
    roles=[RoleType.Searcher, RoleType.FileManager]
)
def keyboard_input(window: UIAWrapper, control: UIAWrapper, keys: str, clear: bool = True,
                   click_enter: bool = False) -> None:
    """You can use this API to simulate the keyboard input.
Parameter:
[Parameter]
Notice:
    This function works with all type of controls.
Examples:
    1. {"func_name": "keyboard_input", "params": {"keys": "hello world", "clear": True}}: This command will clear existing text, then input the text "hello world".
    """
    control.set_focus()
    time.sleep(0.5)
    if str(clear).lower() == "true":
        control.type_keys("{VK_CONTROL down}{a down}{a up}{VK_CONTROL up}{BACKSPACE}", pause=0.1)
        time.sleep(0.3)
    params = dict(pause=0.1, with_spaces=True)
    control.type_keys(keys, **params)
    # 是否按下 Enter
    if str(click_enter).lower() == "true":
        control.type_keys("{ENTER}")
    return None


class OpHotKeyModel(BaseModel):
    keys: List[str] = Field(
        ...,
        description="""The keys to press. For example, ["ctrl", "c"] represents the Ctrl+C shortcut key.
Here are all the keys that can be used: \n{} """.format(", ".join(pyautogui.KEY_NAMES))
    )
    text: str = Field(
        ...,
        description="""The text to input. This parameter is set to an empty string '' if the operation does not require text input.
For example, when you click the Ctrl+F shortcut key, you need to input the text to be searched."""
    )
    click_enter: bool = Field(
        ...,
        description="""Whether to press the Enter button after typing the text. 
    With the exception of recording text, opening applications, etc., almost all other actions require pressing Enter to get new content."""
    )


@OperationRegister(
    model=OpHotKeyModel,
    roles=[RoleType.Searcher, RoleType.FileManager, RoleType.ApplicationManager]
)
def hotkey(window: UIAWrapper, control: UIAWrapper, keys: List[str], text: str, click_enter: bool) -> None:
    """Use this API to simulate the keyboard shortcut keys or press a single key. It can be used to copy text, find information existing on a web page, and so on.
Parameter:
[Parameter]
Notice:
    This function works with all type of controls.
Examples:
    1. {"func_name": "hotkey", "params": {"keys": ["ctrl", "c"], "text": "", "click_enter": False}}: This shortcut copies the selected content.
    2. {"func_name": "hotkey", "params": {"keys": ["ctrl", "f"], "text": "name", "click_enter": True}}: This action opens the text search box and then enters the retrieve name content.
    """
    for k in keys:
        if not pyautogui.isValidKey(k):
            raise ValueError(f"Invalid key: {k}. Expected one of {', '.join(pyautogui.KEY_NAMES)}")

    if window and isinstance(window, UIAWrapper):
        window.set_focus()
    if control and isinstance(control, UIAWrapper):
        control.set_focus()

    time.sleep(0.5)
    if len(keys) == 1:
        pyautogui.press(keys[0])
    else:
        pyautogui.hotkey(*keys)

    if text:
        time.sleep(0.5)
        pyautogui.write(text)
        if click_enter:
            time.sleep(0.5)
            pyautogui.press("enter")
    return None


class OpScrollModel(BaseModel):
    wheel_dist: int = Field(
        ...,
        description="""The distance to scroll. Positive values indicate upward scrolling, negative values indicate downward scrolling.
The larger the value, the larger the scrolling range. Usually the value is 3~9, depending on the task."""
    )


@OperationRegister(
    model=OpScrollModel,
    roles=[RoleType.Searcher, RoleType.FileManager]
)
def scroll(window: UIAWrapper, control: UIAWrapper, wheel_dist: int) -> None:
    """Use to scroll the control item. It typical apply to a ScrollBar type of control item when user request is to scroll the control item, or the targeted control item is not visible nor available in the control item list, but you know the control item is in the application window and you need to scroll to find it.
Parameter:
[Parameter]
Notice:
    This function works with all type of controls.
Examples:
    1. {"func_name": "scroll", "params": {"wheel_dist": 1}}: This command will scroll the control item upward by one unit.
    2. {"func_name": "scroll", "params": {"wheel_dist": -1}}: This command will scroll the control item downward by one unit.
    """
    if window and isinstance(window, UIAWrapper):
        window.set_focus()
        time.sleep(0.5)
    if control and isinstance(control, UIAWrapper):
        control.set_focus()
    time.sleep(0.5)
    pyautogui.scroll(wheel_dist * 120)
    return None


class OpWaitForLoadingModel(BaseModel):
    seconds: int = Field(
        ...,
        description="""The number of seconds to wait for the loading."""
    )


@OperationRegister(
    model=OpWaitForLoadingModel,
    roles=[RoleType.Searcher, RoleType.ApplicationManager, RoleType.FileManager]
)
def wait_for_loading(window: UIAWrapper, control: UIAWrapper, seconds: int = 3) -> None:
    """Waiting for functions to load.
Parameter:
[Parameter]
Notice:
    This function works with all type of controls.
Examples:
    1. {"func_name": "wait_for_loading", "params": {"seconds": 3}}: This operation will wait for 3 seconds.
    """
    time.sleep(seconds)
    return None


class OpOpenApplicationModel(BaseModel):
    app_name: str = Field(
        ...,
        description="""The name of the application to be opened. This parameter is set to empty string '' if the open application is selected from the background"""
    )
    app_label: str = Field(
        ...,
        description="""The label of the application to be opened. This parameter is set to empty string '' if it is not required by any of the applications already in the background."""
    )


@OperationRegister(
    model=OpOpenApplicationModel,
    roles=[RoleType.ApplicationManager]
)
def open_application(window: Any, control: Any, app_name: str = None, app_label: str = None) -> UIAWrapper | None:
    """Open the application with the given name.
Parameter:
[Parameter]
Notice:
    This function will open the desired application.
Examples:
    1. {"func_name": "open_application", "params": {"app_name": "Edge"}}: This command will open the Microsoft Edge application.
    2. {"func_name": "open_application", "params": {"app_label": "1"}}: This command will open the application with label 1.
    """
    if app_label:
        window = wai.active_apps_dict[app_label]
    else:
        window = op_open_application(app_name)
    if window and config["draw_window_outlines"]:
        wai.draw_target_outlines(window, [window], colour="green")
    return window


class OpRunPythonCodeModel(BaseModel):
    code: str = Field(
        ...,
        description="""The Python code to run."""
    )
    main_function: str = Field(
        ...,
        description="""The main function to run. This function is responsible for returning the final result of the run."""
    )


@OperationRegister(
    model=OpRunPythonCodeModel,
    roles=[RoleType.Programmer]
)
def run_python_code(window: Any, control: Any, code: str, main_function: str) -> Any:
    """Run the given Python code.
Parameter:
[Parameter]
Notice:
    This operation is only available to Programmers and returns the result of the code execution.
Examples:
    1. {"func_name": "run_python_code", "params": {"code": "print('Hello, World!')", "main_function": ""}}: This command will print "Hello, World!".
    """
    exec(code, globals())
    if not main_function:
        return None
    if main_function in globals():
        if isinstance(globals()[main_function], Callable):
            return globals()[main_function]()
        else:
            raise ValueError(f"Function {main_function} is not callable.")
    raise ValueError(f"Function {main_function} not found in the code.")


class OpReadFileModel(BaseModel):
    file_path: str = Field(
        ...,
        description="""The file path to be opened."""
    )


@OperationRegister(
    model=OpReadFileModel,
    roles=[RoleType.FileManager]
)
def read_file(window: Any, control: Any, file_path: str) -> Union[str, Dict, Image.Image]:
    """Read the contents of files, including txt, xml, xlsx, csv, docx, png, jpg, pdf ...
Parameter:
[Parameter]
Notice:
    This function only works with txt, xml, xlsx, csv, docx, png, jpg, pdf files.
    The xlsx and csv files return a dict, the png, jpg files return a pil image, and the rest return str.
Examples:
    1. {"func_name": "read_file", "params": {"file_path": "1.txt"}}: This command will read the content of 1.txt.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"`{file_path}` is not exists. Please check the file path.")
    suffix = file_path.suffix
    if suffix in [".txt", ".xml"]:
        with open(file_path, "r", encoding="utf-8") as f:
            result = f.read()
        return result
    elif suffix in [".xlsx", ".csv"]:
        if suffix == ".xlsx":
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
        return df.to_string()
    elif suffix in [".docx"]:
        doc = Document(str(file_path))
        return "\n".join([para.text for para in doc.paragraphs])
    elif suffix in [".png", ".jpg"]:
        img = Image.open(file_path).convert("RGB")
        img = ImageOps.exif_transpose(img)
        img = img.resize((img.size[0] // 2, img.size[1] // 2))
        return img
    elif suffix in [".json"]:
        with open(file_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        return result
    else:
        raise ValueError("This document cannot be textually.")
