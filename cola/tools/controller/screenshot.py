from PIL import Image, ImageDraw, ImageFont, ImageGrab
from pywinauto.controls.uiawrapper import UIAWrapper
from pywinauto.win32structures import RECT
from typing import Dict, List, Tuple
from pathlib import Path
import time
from config.config import Config

config = Config.get_instance()


class Photographer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        pass

    @staticmethod
    def __save_image(image: Image, path: str | Path = None):
        if path is not None:
            image.save(path)

    @staticmethod
    def __draw_rectangles(image: Image.Image, coordinates: List[Tuple[int, int, int, int]],
                          color: str = "red", line_width: int = 3, copy=False) -> Image:
        new_image = image.copy() if copy else image
        draw = ImageDraw.Draw(new_image)
        for coord in coordinates:
            draw.rectangle(coord, outline=color, width=line_width)
        return new_image

    @staticmethod
    def __get_control_coordinates_within_window(control: UIAWrapper, window_rect: RECT) -> Tuple[int, int, int, int]:
        control_rect = control.rectangle()
        x1 = control_rect.left - window_rect.left
        y1 = control_rect.top - window_rect.top
        x2 = control_rect.right - window_rect.left
        y2 = control_rect.bottom - window_rect.top
        return x1, y1, x2, y2

    @staticmethod
    def __draw_annotations(image: Image, coordinate: Tuple[int, int], label_text: str,
                           button_margin: int = 5,
                           border_width: int = 2,
                           font_size: int = 25,
                           font_color: str = "#000000",
                           border_color: str = "#FF0000",
                           button_color: str = "#FFF68F", ) -> Image:
        _ = ImageDraw.Draw(image)
        font = ImageFont.truetype("arial.ttf", font_size)
        text_size = font.getbbox(label_text)

        button_size = (text_size[2] + button_margin, text_size[3] + button_margin)
        button_image = Image.new("RGBA", button_size, button_color)
        button_draw = ImageDraw.Draw(button_image)
        button_draw.text((button_margin // 2, button_margin // 2), label_text,
                         font=font, fill=font_color)
        button_draw.rectangle([(0, 0), (button_size[0] - 1, button_size[1] - 1)],
                              outline=border_color, width=border_width)
        image.paste(button_image, coordinate)
        return image

    def take_application_screenshot(self, window: UIAWrapper, path: str | Path = None) -> Image:
        """Take a screenshot of the application window"""
        window.set_focus()
        time.sleep(1)
        shot = window.capture_as_image()
        self.__save_image(shot, path)
        return shot

    def take_application_screenshot_with_rectangles(self, window: UIAWrapper, controls: List[UIAWrapper],
                                                    color: str = "red", line_width=3,
                                                    save_path: str | Path = None) -> Image:
        """Take a screenshot of the application window and draw a rectangular box of the control on the screenshot"""
        screenshot = self.take_application_screenshot(window)
        window_rect = window.rectangle()

        control_rects = [self.__get_control_coordinates_within_window(control, window_rect)
                         for control in controls if control]
        screenshot = self.__draw_rectangles(screenshot, control_rects, color, line_width)
        self.__save_image(screenshot, save_path)
        return screenshot

    def take_application_screenshot_with_annotations(self, window: UIAWrapper,
                                                     annotation_controls: Dict[str, UIAWrapper],
                                                     color_diff: bool = True,
                                                     color_default: str = "#FFF68F",
                                                     save_path: str | Path = None,
                                                     screenshot: Image = None,
                                                     **kwargs) -> Image:
        window_rect = window.rectangle()
        if screenshot is None:
            screenshot = self.take_application_screenshot(window)
        color_dict = config["annotation_dict"]
        for label_text, control in annotation_controls.items():
            top_left_coord = self.__get_control_coordinates_within_window(control, window_rect)
            top_left_coord = (top_left_coord[0], top_left_coord[1])

            screenshot = self.__draw_annotations(
                screenshot, top_left_coord, label_text,
                button_color=(
                    color_dict.get(
                        control.element_info.control_type, color_default
                    )
                    if color_diff
                    else color_default
                ),
                **kwargs
            )
        self.__save_image(screenshot, save_path)
        return screenshot

    def take_application_with_all(self, window, annotation_controls: Dict[str, UIAWrapper],
                                  rect_color: str = "red", rect_line_width=3,
                                  color_diff: bool = True,
                                  color_default: str = "#FFF68F",
                                  save_path: str | Path = None,
                                  **kwargs) -> Image:
        screenshot = self.take_application_screenshot_with_rectangles(
            window, list(annotation_controls.values()), rect_color, rect_line_width, None)
        screenshot = self.take_application_screenshot_with_annotations(
            window, annotation_controls, color_diff, color_default, None, screenshot, **kwargs)
        self.__save_image(screenshot, save_path)
        return screenshot

    def take_desktop_screenshot(self, path: str | Path = None, all_screens=False) -> Image:
        screenshot = ImageGrab.grab(all_screens=all_screens)
        self.__save_image(screenshot, path)
        return screenshot
