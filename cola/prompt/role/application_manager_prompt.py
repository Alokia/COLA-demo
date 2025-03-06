from cola.fundamental.base_prompt import BasePrompt
from typing import Dict, List, Union
from cola.tools.controller.inspector import WindowsApplicationInspector
from config.config import Config
from cola.tools.op import get_ops_description
from cola.utils.print_utils import any_to_str
from pywinauto.controls.uiawrapper import UIAWrapper


config = Config.get_instance()
wai = WindowsApplicationInspector()


class ApplicationManagerPrompt(BasePrompt):
    def __init__(self):
        super().__init__()
        self.template_folder = config["root_path"] / "cola/prompt_templates/role/application_manager"

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

    def create_step_user_prompt(self, data) -> Dict[str, str]:
        active_app_info_str = wai.get_active_application(refresh=True, return_str=True)
        content_list = []

        content_list.extend([
            "Here are the subtasks you need to complete, [current subtasks]: {}".format(any_to_str(data.role_tasks)),
            "This is the currently open application: \n{}".format(active_app_info_str),
        ])

        if "result" in data and data.result and not isinstance(data.result, UIAWrapper):
            content_list.extend([
                "This is the result from the previous step: \n ",
                data.result,
                "Make sure that this result is what is needed, if it is and the current task has been completed in full, then you can set branch to `RoleTaskFinish`."
            ])
        elif "result" in data and data.result and isinstance(data.result, UIAWrapper):
            content_list.extend([
                "This is the result from the previous step: \n {}".format(data.result),
                "If this is the application required by the task, the task is complete and the `branch` is set to `RoleTaskFinish`"
            ])
        else:
            content_list.extend([
                "No execution result is currently received, so branch cannot be set to `RoleTaskFinish`."
            ])

        content_list.extend(self.catch(data, "feedback"))
        content_list.extend(self.catch(data, "message"))

        content_list.append(
            "Please learn from Example's experience, and the above task information, and give your response:"
        )
        return self.create_user_prompt(content_list)
