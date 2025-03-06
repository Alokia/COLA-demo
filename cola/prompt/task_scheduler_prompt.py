from typing import List, Dict
from cola.fundamental.base_prompt import BasePrompt
from config.config import Config
from cola.utils.print_utils import any_to_str

config = Config.get_instance()


class TaskSchedulerPrompt(BasePrompt):
    def __init__(self, agents_capability: Dict[str, str]):
        self.template_folder = config["root_path"] / "cola/prompt_templates/task_scheduler"
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

    def create_distribute_subtasks_user_prompt(self, data) -> Dict[str, str]:
        content_list = []

        content_list.extend([
            "Please distribute the following subtasks to the corresponding agents. Make sure that all subtasks are assigned and that the results are ordered in the order of the subtasks."
            "This is the [total subtasks] that needs to be assigned: {}".format(any_to_str(data.sub_tasks)),
        ])

        if ("problem" in data and data.problem) and ("role_tasks" in data and data.role_tasks):
            content_list.extend([
                "Here's some feedback from {}.\n".format(data.sender),
                "[Previously assigned subtasks]: {}.\n Some feedback received: {}".format(
                    any_to_str(data.role_tasks), data.problem
                ),
                "Please think deeply about the issues mentioned in the feedback and rework the new distribution scheme starting with the subtasks in the feedback."
                "Note: Please reassign the tasks starting with [Previously assigned subtasks] in [total subtasks] and the tasks following it."
            ])

        content_list.extend(self.catch(data, "message"))

        content_list.append(
            "Please learn from Example's experience, and the above task information, and give your response:"
        )

        return self.create_user_prompt(content_list)
