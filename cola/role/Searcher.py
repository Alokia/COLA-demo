from cola.fundamental import BaseRole, BaseRoleResponseFormat
from typing import List, Optional, Dict, Any, Union, Callable
from cola.utils.datatype import WorkflowEvent, RoleType
from cola.prompt.role.searcher_prompt import SearcherPrompt
from cola.utils.agent_utils import RegisterAgent
from cola.utils.data_utils import PrivateData
from pydantic import BaseModel, Field
from config.config import Config
from cola.tools.controller.inspector import WindowsApplicationInspector
from cola.tools.controller.screenshot import Photographer
from pywinauto.controls.uiawrapper import UIAWrapper

config = Config.get_instance()
wai = WindowsApplicationInspector()
capturer = Photographer()

_rf_params = dict(
    role=RoleType.Searcher,
    additional_branch_type=None,
    additional_branch_desc=None,
)


class SearcherResponseFormat(BaseRoleResponseFormat(**_rf_params)):
    observation: str = Field(
        ...,
        description="Give a detailed description of the current scene based on the current screenshot and the task to be accomplished."
    )
    information: str = Field(
        ...,
        description="If the current scenario is relevant to the question to be answered, extract useful information from it that will be used as a basis for answering the question."
                    " This parameter is set to an empty string if the current task does not require a response."
    )
    selected_control: Optional[str] = Field(
        ...,
        description="The label of the chosen control for the operation."
                    " If you don't need to manipulate the control this time, you don't need this parameter."
    )


@RegisterAgent(ignore_capability=False)
class Searcher(BaseRole):
    role = RoleType.Searcher
    capability = ("Can use an opened browser to search for information, open web pages, etc."
                  " Can also do everything related to web pages, such as playing videos in web pages, opening files, reading documents in web pages, and so on."
                  " Cannot do any other tasks beyond that, including opening a browser.")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.prompter: SearcherPrompt = SearcherPrompt()
        self.session_step = {
            "Execute Steps": [],
            "Experience": []
        }

    def branch_step(self, response: Dict, data: Optional[PrivateData] = None, **kwargs) -> PrivateData:
        if (branch := response["branch"]) == "Continue":
            target_control = None
            if response["selected_control"]:
                target_control = wai.app_elements_dict[response["selected_control"]]
                if config["draw_selected_element_outlines"]:
                    wai.draw_target_outlines(target_control, [target_control], colour="red")

            return PrivateData(
                sender=self.role, receiver=RoleType.Executor, event=WorkflowEvent.Executor_execute_op,
                target_window=data.target_window,
                target_control=target_control, operation=response["operation"],
                intend=response["intention"], message=response["message"],
                handle_event=response["handle_event"]
            )
        elif branch == "RoleTaskFinish":
            return PrivateData(
                sender=self.role, receiver=RoleType.TaskScheduler,
                event=WorkflowEvent.TaskScheduler_distribute_next_subtask,
                information=response["information"],
                message=response["message"]
            )
        elif branch == "TaskMismatch":
            return PrivateData(
                sender=self.role, receiver=RoleType.TaskScheduler,
                event=WorkflowEvent.TaskScheduler_distribute_subtask,
                role_tasks=data.role_tasks,
                problem=response["problem"], message=response["message"],
            )
        else:
            raise ValueError(f"Unknown branch type: {branch} in {self.role}")

    @BaseRole.register_event(WorkflowEvent.Role_step)
    def handle_step(self, data: PrivateData, handoff: bool, **kwargs) -> Optional[PrivateData]:
        """
        expected keys:
         - target_window
         - role_tasks
         - feedback
         - result
         - message
        """
        if "target_window" not in data:
            return PrivateData(
                sender=self.role, receiver=RoleType.Planner, event=WorkflowEvent.Planner_make_sub_task,
                remake_plan=f"{self.role}: I need a opened browser to search for information. But the browser is not opened yet. Please open the browser first.",
                role_tasks=data.role_tasks
            )

        window: UIAWrapper = data.target_window
        if config["draw_window_outlines"]:
            wai.draw_target_outlines(window, [window], colour="green")

        if not handoff:
            if "role_tasks" in data:
                self.cdc.summary_context[self.role].role_tasks = data.role_tasks

            self.episodic_messages = [
                self.prompter.create_system_prompt(SearcherResponseFormat, self.role),
                *self.retrieve_long_term_memory(self.generate_summary())
            ]
            self.linked_messages = self.retrieve_short_term_memory()
            self.query_messages = [
                self.prompter.create_step_user_prompt(data)
            ]

            origin_response, response = self.query(format_model=SearcherResponseFormat)
            if origin_response is None and response is None and self.cdc.switch_to is not None:
                return None
        else:
            origin_response, response = self.handoff_query()

        if response["information"]:
            self.cdc.role_context.role_infos.append(response["information"])

        # record execution steps
        self.record_session_step(step=dict(
            thought_process=response["thought_process"],
            intention=response["intention"],
            selected_control=response["selected_control"],
            operation=response["operation"],
            information=response["information"], branch=response["branch"],
        ))

        response["handle_event"] = WorkflowEvent.Role_step

        self.store_short_term_memory({
            "Observation": response["observation"],
            "Intend": response["intention"],
            "Plan": response["local_plan"],
            "Summary": response["summary"]
        })

        return self.branch_step(response, data=data)
