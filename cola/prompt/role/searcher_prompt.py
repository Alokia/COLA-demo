from cola.fundamental.base_prompt import BasePrompt
from typing import Dict, List, Union
from cola.tools.controller.inspector import WindowsApplicationInspector
from config.config import Config
from cola.tools.controller.screenshot import Photographer
from cola.tools.op import get_ops_description
from pywinauto.controls.uiawrapper import UIAWrapper
from cola.utils.print_utils import any_to_str

config = Config.get_instance()
capturer = Photographer()
wai = WindowsApplicationInspector()


class SearcherPrompt(BasePrompt):
    def __init__(self):
        super().__init__()
        self.template_folder = config["root_path"] / "cola/prompt_templates/role/searcher"

    def create_system_prompt(self, format_model, role) -> Dict[str, str]:
        system_prompt_template = self.load_template(self.template_folder / "system_template.txt")
        available_operation = get_ops_description(role=role)

        return {
            "role": "system",
            "content": system_prompt_template.format(
                format_description=self.format_description(format_model),
                available_operation=available_operation
            )
        }

    def create_step_user_prompt(self, data) -> Dict[str, Union[str, List]]:
        window = data.target_window

        ele_str = wai.get_application_elements(window, refresh=True, return_str=True)
        if config["draw_all_element_outlines"]:
            wai.draw_target_outlines(window, wai.app_elements_list, colour="green")

        content_list = []
        content_list.extend([
            "This is the current screenshot of the application window.",
            capturer.take_application_screenshot(window),
            "This is the all controls in the application window: \n{}".format(ele_str),
            "And this is the annotation of the controls in the application window.",
            capturer.take_application_screenshot_with_annotations(window, wai.app_elements_dict),
        ])
        content_list.extend([
            "This is the overall mission: {}".format(data.task),
            "This is the question the mission needs to answer: {}".format(
                data.question) if data.question else "This task does not need to be answered.",
            "Here are the subtasks you need to complete, [current subtasks]: {}".format(any_to_str(data.role_tasks)),
            "Make sure your next action is within [current subtasks], don't go ahead and do something that exceeds current subtasks based on the [current subtasks]."
        ])

        content_list.extend(self.catch(data, "feedback"))
        content_list.extend(self.catch(data, "result"))
        content_list.extend(self.catch(data, "message"))

        content_list.append(
            "Please learn from Example's experience, and the above task information, and give your response:"
        )

        step_prompt = self.create_user_prompt(content_list)
        return step_prompt
