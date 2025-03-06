from cola.fundamental import BaseRole, BaseRoleResponseFormat
from typing import Optional, Dict, List
from cola.utils.datatype import WorkflowEvent, RoleType
from cola.utils.agent_utils import RegisterAgent
from cola.utils.data_utils import PrivateData
from pydantic import BaseModel, Field
from config.config import Config
from cola.tools.controller.screenshot import Photographer
from cola.tools.controller.inspector import WindowsApplicationInspector
from cola.prompt.role.programmer_prompt import ProgrammerPrompt
from enum import Enum
from cola.tools.op import OpType
from pywinauto.controls.uiawrapper import UIAWrapper

config = Config.get_instance()
wai = WindowsApplicationInspector()
capturer = Photographer()

_rf_params = dict(
    role=RoleType.Programmer,
    additional_branch_type=None,
    additional_branch_desc=None,
)


class ProgrammerResponseFormat(BaseRoleResponseFormat(**_rf_params)):
    analyze: str = Field(
        ...,
        description="Give your process for analyzing the scenario."
    )
    answer: str = Field(
        ...,
        description="If the task requires an answer, give a thoughtful answer. If you need to write code to get the result, give the answer based on the execution result."
                    " If answer is not empty, the task is completed and the branch is set to `RoleTaskFinish`."
    )


@RegisterAgent(ignore_capability=False)
class Programmer(BaseRole):
    role = RoleType.Programmer
    capability = "Possesses logical reasoning and analytical skills. Can reason to arrive at an answer to a question or write Python code to get the result."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.prompter: ProgrammerPrompt = ProgrammerPrompt()
        self.session_step = {
            "Execute Steps": [],
            "Experience": []
        }

    def branch_step(self, response: Dict, **kwargs) -> PrivateData:
        if (branch := response["branch"]) == "Continue":
            return PrivateData(
                sender=self.role, receiver=RoleType.Executor, event=WorkflowEvent.Executor_execute_op,
                operation=response["operation"], not_track=True,
                intend=response["intention"], message=response["message"],
                handle_event=response["handle_event"]
            )
        elif branch == "RoleTaskFinish":
            return PrivateData(
                sender=self.role, receiver=RoleType.TaskScheduler,
                event=WorkflowEvent.TaskScheduler_distribute_next_subtask,
                information=response["answer"],
                message=response["message"]
            )
        elif branch == "TaskMismatch":
            return PrivateData(
                sender=self.role, receiver=RoleType.TaskScheduler,
                event=WorkflowEvent.TaskScheduler_distribute_subtask,
                role_tasks=self.cdc.p[self.role].role_tasks,
                problem=response["problem"], message=response["message"]
            )
        else:
            raise ValueError(f"Unknown branch type: {branch} in {self.role}")

    @BaseRole.register_event(WorkflowEvent.Role_step)
    def handle_step(self, data: PrivateData, handoff: bool, **kwargs) -> Optional[PrivateData]:
        """
        expected keys:
         - role_tasks
         - feedback
         - result
         - message
        """
        if not handoff:
            if "role_tasks" in data:
                self.cdc.summary_context[self.role].role_tasks = data.role_tasks

            self.episodic_messages = [
                self.prompter.create_system_prompt(ProgrammerResponseFormat, self.role),
                *self.retrieve_long_term_memory(self.generate_summary())
            ]
            self.linked_messages = self.retrieve_short_term_memory()
            self.query_messages = [
                self.prompter.create_step_user_prompt(data)
            ]

            origin_response, response = self.query(format_model=ProgrammerResponseFormat)
            if origin_response is None and response is None and self.cdc.switch_to is not None:
                return None
        else:
            origin_response, response = self.handoff_query()

        if response["answer"]:
            self.cdc.role_context.role_infos.append(response["answer"])

        # record execution steps
        self.record_session_step(step=dict(
            thought_process=response["thought_process"],
            intention=response["intention"], operation=response["operation"],
            answer=response["answer"], branch=response["branch"],
        ))

        response["handle_event"] = WorkflowEvent.Role_step

        self.store_short_term_memory({
            "Analyze": response["analyze"],
            "Intend": response["intention"],
            "Plan": response["local_plan"],
            "Summary": response["summary"]
        })

        return self.branch_step(response, data=data)
