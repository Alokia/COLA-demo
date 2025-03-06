from cola.fundamental import BaseRole, BaseRoleResponseFormat
from typing import Optional, Dict
from cola.utils.datatype import WorkflowEvent, RoleType
from cola.utils.agent_utils import RegisterAgent
from cola.utils.data_utils import PrivateData
from pydantic import BaseModel, Field
from config.config import Config
from cola.tools.controller.screenshot import Photographer
from cola.tools.controller.inspector import WindowsApplicationInspector
from cola.prompt.role.application_manager_prompt import ApplicationManagerPrompt
from pywinauto.controls.uiawrapper import UIAWrapper

config = Config.get_instance()
wai = WindowsApplicationInspector()
capturer = Photographer()

_rf_params = dict(
    role=RoleType.ApplicationManager,
    additional_branch_type=None,
    additional_branch_desc=dict(
        RoleTaskFinish="`RoleTaskFinish` can only be set when a result is obtained."
    ),
)


class ApplicationManagerResponseFormat(BaseRoleResponseFormat(**_rf_params)):
    analyze: str = Field(
        ...,
        description="Give your process for analyzing the scenario."
    )


@RegisterAgent(ignore_capability=False)
class ApplicationManager(BaseRole):
    role = RoleType.ApplicationManager
    capability = "Can open applications such as browsers, explorers, chat software, etc. Cannot do any other tasks beyond that."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.prompter: ApplicationManagerPrompt = ApplicationManagerPrompt()
        self.session_step = {
            "Execute Steps": [],
            "Experience": []
        }

    def branch_step(self, response: Dict, **kwargs) -> PrivateData:
        if (branch := response["branch"]) == "Continue":
            return PrivateData(
                sender=self.role, receiver=RoleType.Executor, event=WorkflowEvent.Executor_execute_op,
                operation=response["operation"],
                intend=response["intention"], message=response["message"],
                handle_event=response["handle_event"]
            )
        elif branch == "RoleTaskFinish":
            return PrivateData(
                sender=self.role, receiver=RoleType.TaskScheduler, message=response["message"],
                event=WorkflowEvent.TaskScheduler_distribute_next_subtask,
            )
        elif branch == "TaskMismatch":
            return PrivateData(
                sender=self.role, receiver=RoleType.TaskScheduler,
                event=WorkflowEvent.TaskScheduler_distribute_subtask,
                role_tasks=self.cdc.role_context.role_tasks,
                problem=response["problem"],
                message=response["message"],
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
                self.prompter.create_system_prompt(ApplicationManagerResponseFormat, self.role),
                *self.retrieve_long_term_memory(self.generate_summary())
            ]
            self.linked_messages = self.retrieve_short_term_memory()
            self.query_messages = [
                self.prompter.create_step_user_prompt(data)
            ]

            origin_response, response = self.query(format_model=ApplicationManagerResponseFormat)
            if origin_response is None and response is None and self.cdc.switch_to is not None:
                return None
        else:
            origin_response, response = self.handoff_query()

        # record execution steps
        self.record_session_step(step=dict(
            thought_process=response["thought_process"],
            intention=response["intention"], operation=response["operation"],
            branch=response["branch"],
        ))

        response["handle_event"] = WorkflowEvent.Role_step

        if "result" in data and isinstance(data.result, UIAWrapper):
            self.cdc.role_context.target_window = data.result
            self.cdc.role_context.pop("result")

        self.store_short_term_memory({
            "Analyze": response["analyze"],
            "Intend": response["intention"],
            "Summary": response["summary"]
        })

        return self.branch_step(response, data=data)
