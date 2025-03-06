from typing import Dict
from cola.fundamental.base_prompt import BasePrompt
from config.config import Config
from cola.utils.print_utils import any_to_str
from cola.tools.op import get_ops_function_dict

config = Config.get_instance()


class ReviewerPrompt(BasePrompt):
    def __init__(self):
        self.template_folder = config["root_path"] / "cola/prompt_templates/reviewer"

    def create_system_prompt(self, format_model) -> Dict[str, str]:
        system_template = self.load_template(self.template_folder / "system_template.txt")

        return {
            "role": "system",
            "content": system_template.format(
                ops_function=any_to_str(get_ops_function_dict()),
                format_description=self.format_description(format_model)
            )
        }

    def create_track_state_user_prompt(self, data) -> Dict[str, str]:
        content_list = []

        if ("track_before_state" in data and data.track_before_state) and (
                "track_after_state" in data and data.track_after_state):
            content_list.extend([
                "Below is a screenshot of the desktop before performing the operation:",
                data.track_before_state,
                "This is the operation performed: {}.".format(data.execute_op),
                "Below is a screenshot of the desktop after performing the operation:",
                data.track_after_state,
                "This is the intent to perform the action: {}.".format(data.intend),
            ])
        else:
            content_list.extend([
                "This is the operation performed: {}.".format(data.execute_op),
                "This is the intent to perform the action: {}.".format(data.intend),
            ])

        if "result" in data and data.result:
            result = "{}".format(data.result)
            if len(result) > 10000:
                result = result[:10000] + "..."
            content_list.extend([
                "This is the result of the operation: ",
                result
            ])
        content_list.extend(self.catch(data, "message"))

        content_list.extend([
            "Please learn from Example's experience, and the above task information, and give your response:"
        ])

        return self.create_user_prompt(content_list)
