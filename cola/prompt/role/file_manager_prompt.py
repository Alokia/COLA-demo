from cola.fundamental.base_prompt import BasePrompt
from typing import Dict, List, Union
from cola.tools.controller.inspector import WindowsApplicationInspector
from config.config import Config
from cola.tools.controller.screenshot import Photographer
from cola.tools.op import get_ops_description
from cola.utils.print_utils import any_to_str

config = Config.get_instance()
capturer = Photographer()
wai = WindowsApplicationInspector()


class FileManagerPrompt(BasePrompt):
    def __init__(self):
        super().__init__()
        self.template_folder = config["root_path"] / "cola/prompt_templates/role/file_manager"

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
        content_list = []

        content_list.extend([
            "This is the overall mission: {}".format(data.task),
            "This is the question the mission needs to answer: {}".format(
                data.question) if data.question else "This task does not need to be answered.",
            "Please analyze the following scenario carefully and answer the questions after a step-by-step process of reflection.",
            "If you need to execute code to get the result, make sure you use a function to get the result."
            "Task: \n{}\n".format(data.role_tasks),
        ])

        content_list.extend(self.catch(data, "feedback"))
        content_list.extend(self.catch(data, "message"))

        if "result" in data and data.result:
            content_list.extend([
                "This is the result from the previous step: \n {}".format(data.result),
                "Make sure that this result is what is needed, if it is and the current task has been completed in full, then you can set branch to `RoleTaskFinish`."
            ])
        else:
            content_list.extend([
                "No execution result is currently received, so branch cannot be set to `RoleTaskFinish`."
            ])

        content_list.append(
            "Please learn from Example's experience, and the above task information, and give your response:"
        )

        return self.create_user_prompt(content_list)
