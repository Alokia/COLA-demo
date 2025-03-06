from pyscreeze import screenshot
from pywinauto import Desktop
from pywinauto.controls.uiawrapper import UIAWrapper
from typing import Dict, List, Tuple, Union
from abc import ABC, abstractmethod
import psutil
from config.config import Config
import time

config = Config.get_instance()


class BackendFactory:
    """
    A factory class to create backend strategies.
    """

    @staticmethod
    def create_backend(backend: str) -> "BackendStrategy":
        """
        Create a backend strategy.
        :param backend: The backend to use.
        :return: The backend strategy.
        """
        if backend == "uia":
            return UIABackendStrategy()
        elif backend == "win32":
            return Win32BackendStrategy()
        else:
            raise ValueError(f"Backend {backend} not supported")


class BackendStrategy(ABC):
    """
    Define an interface for backend strategies.
    """

    @abstractmethod
    def get_desktop_windows(self, remove_empty: bool) -> List[UIAWrapper]:
        """
        Get all the apps on the desktop.
        :param remove_empty: Whether to remove empty titles.
        :return: The apps on the desktop.
        """
        pass

    @abstractmethod
    def find_control_elements_in_descendants(
            self,
            window: UIAWrapper,
            control_type_list: List[str] = None,
            class_name_list: List[str] = None,
            title_list: List[str] = None,
            is_visible: bool = True,
            is_enabled: bool = True,
            depth: int = 0,
    ) -> List[UIAWrapper]:
        """
        Find control elements in descendants of the window.
        :param window: The window to find control elements.
        :param control_type_list: The control types to find.
        :param class_name_list: The class names to find.
        :param title_list: The titles to find.
        :param is_visible: Whether the control elements are visible.
        :param is_enabled: Whether the control elements are enabled.
        :param depth: The depth of the descendants to find.
        :return: The control elements found.
        """
        pass


class UIABackendStrategy(BackendStrategy):
    """
    The backend strategy for UIA.
    """

    def get_desktop_windows(self, remove_empty: bool) -> List[UIAWrapper]:
        """
        Get all the apps on the desktop.
        :param remove_empty: Whether to remove empty titles.
        :return: The apps on the desktop.
        """
        desktop_windows = Desktop(backend="uia").windows()
        if remove_empty:
            desktop_windows = [
                app
                for app in desktop_windows
                if app.window_text() != "" and app.element_info.class_name not in ["IME", "MSCTFIME UI"]
            ]
        return desktop_windows

    def find_control_elements_in_descendants(
            self,
            window: UIAWrapper,
            control_type_list: List[str] = None,
            class_name_list: List[str] = None,
            title_list: List[str] = None,
            is_visible: bool = True,
            is_enabled: bool = True,
            depth: int = 0,
    ) -> List[UIAWrapper]:
        """
        Find control elements in descendants of the window for uia backend.
        :param window: The window to find control elements.
        :param control_type_list: The control types to find.
        :param class_name_list: The class names to find.
        :param title_list: The titles to find.
        :param is_visible: Whether the control elements are visible.
        :param is_enabled: Whether the control elements are enabled.
        :param depth: The depth of the descendants to find.
        :return: The control elements found.
        """

        if window is None:
            return []

        control_elements = []
        if not control_type_list:
            control_elements += window.descendants()
        else:
            for control_type in control_type_list:
                if depth == 0:
                    sub_controls = window.descendants(control_type=control_type)
                else:
                    sub_controls = window.descendants(control_type=control_type, depth=depth)
                control_elements += sub_controls

        if is_visible:
            control_elements = [control for control in control_elements if control.is_visible()]
        if is_enabled:
            control_elements = [control for control in control_elements if control.is_enabled()]
        if title_list:
            control_elements = [
                control
                for control in control_elements
                if control.window_text() in title_list
            ]
        if class_name_list:
            control_elements = [
                control
                for control in control_elements
                if control.element_info.class_name in class_name_list
            ]

        return control_elements


class Win32BackendStrategy(BackendStrategy):
    """
    The backend strategy for Win32.
    """

    def get_desktop_windows(self, remove_empty: bool) -> List[UIAWrapper]:
        """
        Get all the apps on the desktop.
        :param remove_empty: Whether to remove empty titles.
        :return: The apps on the desktop.
        """

        desktop_windows = Desktop(backend="win32").windows()
        desktop_windows = [app for app in desktop_windows if app.is_visible()]

        if remove_empty:
            desktop_windows = [
                app
                for app in desktop_windows
                if app.window_text() != "" and app.element_info.class_name not in ["IME", "MSCTFIME UI"]
            ]
        return desktop_windows

    def find_control_elements_in_descendants(
            self,
            window: UIAWrapper,
            control_type_list: List[str] = None,
            class_name_list: List[str] = None,
            title_list: List[str] = None,
            is_visible: bool = True,
            is_enabled: bool = True,
            depth: int = 0,
    ) -> List[UIAWrapper]:
        """
        Find control elements in descendants of the window for win32 backend.
        :param window: The window to find control elements.
        :param control_type_list: The control types to find.
        :param class_name_list: The class names to find.
        :param title_list: The titles to find.
        :param is_visible: Whether the control elements are visible.
        :param is_enabled: Whether the control elements are enabled.
        :param depth: The depth of the descendants to find.
        :return: The control elements found.
        """

        if window is None:
            return []

        control_elements = []
        if not class_name_list:
            control_elements += window.descendants()
        else:
            for class_name in class_name_list:
                if depth == 0:
                    sub_controls = window.descendants(class_name=class_name)
                else:
                    sub_controls = window.descendants(class_name=class_name, depth=depth)
                control_elements += sub_controls

        if is_visible:
            control_elements = [control for control in control_elements if control.is_visible()]
        if is_enabled:
            control_elements = [control for control in control_elements if control.is_enabled()]
        if title_list:
            control_elements = [
                control
                for control in control_elements
                if control.window_text() in title_list
            ]
        if control_type_list:
            control_elements = [
                control
                for control in control_elements
                if control.element_info.control_type in control_type_list
            ]

        return [
            control for control in control_elements if control.element_info.name != ""
        ]


class WindowsApplicationInspector:
    _instance = None

    def __new__(cls, backend: str = config["backend"]):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, backend: str = config["backend"]):
        self.backend_method = BackendFactory.create_backend(backend)

        self.active_apps_list: List[UIAWrapper] | None = None
        self.active_apps_dict: Dict[str, UIAWrapper] | None = None
        self.app_elements_list: List[UIAWrapper] | None = None
        self.app_elements_dict: Dict[str, UIAWrapper] | None = None

    def _get_info(self, window: UIAWrapper,
                  field_list: List[str] = None,
                  max_length: int = 50,
                  drop_max: bool = False) -> Dict:
        if field_list is None:
            field_list = ["control_type", "control_id", "class_name", "name", "rectangle", "window_text", "root_name"]
        info = {}
        try:
            for field in field_list:
                if field == "window_text":
                    v = window.window_text()
                    if len(str(v)) > max_length:
                        v = str(v)[:max_length] + "..." if not drop_max else "..."
                    info[field] = v
                elif field == "root_name":
                    info[field] = self.get_application_root_name(window)
                else:
                    if hasattr(window.element_info, field) and (v := getattr(window.element_info, field)):
                        if len(str(v)) > max_length:
                            v = str(v)[:max_length] + "..." if not drop_max else "..."
                        info[field] = v
        except:
            return {}
        return info

    @staticmethod
    def _dict_to_str(elements: Dict):
        elements_info = []
        for k, v in elements.items():
            info = "    - \"label\": {}".format(k)
            for key, value in v.items():
                if key == "control_rect":
                    continue
                info += ", \"{}\": {}".format(key, value)
            elements_info.append(info)
        return "\n".join(elements_info)

    def get_active_application(self, refresh: bool = True,
                               remove_empty: bool = True,
                               return_str: bool = False,
                               field_list: List[str] = None,
                               max_length: int = 50,
                               drop_max: bool = False) -> (
            Union)[str, Tuple[List[UIAWrapper], Dict[str, UIAWrapper]]]:
        """Get the currently active application of the operating system
        Parameters:
            refresh: Whether to re-test the active application
            remove_empty: Whether to filter out applications with an empty window_text
            return_str: Whether to return a formatted string
            field_list: Fields reserved for formatting strings, see _get_info
            max_length: Maximum string length, see _get_info
            drop_max: Whether to exclude strings that exceed max_length, see _get_info
        """
        if refresh:
            self.active_apps_list = self.backend_method.get_desktop_windows(remove_empty=remove_empty)
            self.active_apps_dict = {str(k): v for k, v in enumerate(self.active_apps_list)}
        if return_str:
            if field_list is None:
                field_list = ["name", "control_type", "root_name"]
            apps_dict = {
                k: self._get_info(v, field_list, max_length, drop_max)
                for k, v in self.active_apps_dict.items()
            }
            return self._dict_to_str(apps_dict)
        return self.active_apps_list, self.active_apps_dict

    def target_new_opened_application(self, refresh: bool = True, remove_empty: bool = True) -> UIAWrapper | None:
        """Find the emerging application from the current list of new active windows
        Parameters:
            refresh: Whether to overwrite the original record
            remove_empty: Whether to filter out applications with an empty window_text
        """
        new_active_app_list = self.backend_method.get_desktop_windows(remove_empty=remove_empty)
        new_app = None
        for app in new_active_app_list:
            if app not in self.active_apps_list:
                new_app = app
                break
        if refresh:
            self.active_apps_list = new_active_app_list
            self.active_apps_dict = {str(k): v for k, v in enumerate(self.active_apps_list)}
        return new_app

    def target_app_based_root_name(self, root_name: str) -> UIAWrapper | None:
        """Locate the application by root name
        """
        window = None
        for app in self.active_apps_list:
            if self.get_application_root_name(app) == root_name:
                window = app
                break
        return window

    def get_application_elements(self, window: UIAWrapper,
                                 control_type_list: List[str] = None,
                                 class_name_list: List[str] = None,
                                 title_list: List[str] = None,
                                 is_visible: bool = True,
                                 is_enabled: bool = True,
                                 depth: int = 0,
                                 refresh: bool = True,
                                 return_str: bool = False,
                                 field_list: List[str] = None,
                                 max_length: int = 50,
                                 drop_max: bool = False) -> (
            Union)[str, Tuple[List[UIAWrapper], Dict[str, UIAWrapper]]]:
        """Get all child controls of the application
        Parameters:
            window: Target application
            control_type_list: Types of controls to be retained
            class_name_list: Class name to be retained
            title_list: title to be retained
            is_visible: Whether the child control needs to be visible
            is_enabled: Whether the child control needs to be available
            depth: Depth of detection

            refresh: Whether to re-test the active application
            return_str: Whether to return a formatted string
            field_list: see _get_info
            max_length: see _get_info
            drop_max: see _get_info
        """
        if control_type_list is None:
            control_type_list = config["control_list"]
        if refresh:
            self.app_elements_list = self.backend_method.find_control_elements_in_descendants(
                window,
                control_type_list=control_type_list,
                class_name_list=class_name_list,
                title_list=title_list,
                is_visible=is_visible,
                is_enabled=is_enabled,
                depth=depth
            )
            self.app_elements_dict = {str(k): v for k, v in enumerate(self.app_elements_list)}
        if return_str:
            if field_list is None:
                field_list = ["name", "control_type", "class_name", "window_text", "control_id"]
            app_elements = {
                k: self._get_info(v, field_list, max_length, drop_max)
                for k, v in self.app_elements_dict.items()
            }
            return self._dict_to_str(app_elements)
        return self.app_elements_list, self.app_elements_dict

    @staticmethod
    def get_application_root_name(window: UIAWrapper) -> str:
        if window is None:
            return ""
        process_id = window.process_id()
        try:
            process = psutil.Process(process_id)
            return process.name()
        except psutil.NoSuchProcess:
            return ""

    @staticmethod
    def draw_target_outlines(window: UIAWrapper, target_elements: List[UIAWrapper], colour="red"):
        window.set_focus()
        time.sleep(1)
        for target in target_elements:
            target.draw_outline(colour=colour)