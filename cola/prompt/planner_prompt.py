from typing import Dict
from cola.fundamental.base_prompt import BasePrompt
from config.config import Config
from cola.utils.print_utils import any_to_str

config = Config.get_instance()


class PlannerPrompt(BasePrompt):
    def __init__(self, agents_capability: Dict[str, str]):
        self.template_folder = config["root_path"] / "cola/prompt_templates/planner"
        self.agents_capability = agents_capability

    def create_system_prompt(self, format_model) -> Dict[str, str]:
        system_template = self.load_template(self.template_folder / "system_template.txt")

        return {
            "role": "system",
            "content": system_template.format(
                role_capabilities=any_to_str(self.agents_capability),
                format_description=self.format_description(format_model)
            )
        }

    def create_make_sub_task_user_prompt(self, data) -> Dict[str, str]:
        content_list = []

        content_list.extend([
            "Task: {}".format(data.task),
        ])

        if "problem" in data and data.problem:
            content_list.extend([
                "This is feedback from {}: {}".format(data.sender, data.problem),
            ])

        content_list.extend(self.catch(data, "message"))

        content_list.append(
            "Please learn from Example's experience, and the above task information, and give your response:"
        )

        return self.create_user_prompt(content_list)

    def create_answer_system_prompt(self, format_model) -> Dict[str, str]:
        system_template = self.load_template(self.template_folder / "answer_template.txt")

        return {
            "role": "system",
            "content": system_template.format(
                format_description=self.format_description(format_model)
            )
        }

    def create_answer_user_prompt(self, data) -> Dict[str, str]:
        content_list = []

        if "role_feedback" in data:
            content_list.extend([
                "This is the question you need to answer: \n{}".format(data.question),
                "This is the information from {}: \n{}".format(data.sender, any_to_str(data.role_infos)),
            ])

        content_list.append(
            "Please give your answer based on the above information, your answer:"
        )

        return self.create_user_prompt(content_list)
