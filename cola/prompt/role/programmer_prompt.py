from cola.fundamental.base_prompt import BasePrompt
from typing import Dict, List, Union
from cola.tools.controller.inspector import WindowsApplicationInspector
from config.config import Config
from cola.tools.op import get_ops_description
from cola.utils.print_utils import any_to_str

config = Config.get_instance()
wai = WindowsApplicationInspector()


class ProgrammerPrompt(BasePrompt):
    def __init__(self):
        super().__init__()
        self.template_folder = config["root_path"] / "cola/prompt_templates/role/programmer"

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

        if "file_content" in data and data.file_content:
            content_list.extend([
                "This is the content of the file: \n",
                data.file_content,
                "Please analyze the content of the file and give your intentions for the next step."
            ])

        content_list.extend(self.catch(data, "feedback"))
        content_list.extend(self.catch(data, "result"))
        content_list.extend(self.catch(data, "message"))

        content_list.append(
            "Please learn from Example's experience, and the above task information, and give your response:"
        )

        return self.create_user_prompt(content_list)
