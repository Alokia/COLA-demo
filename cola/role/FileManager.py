from cola.fundamental import BaseRole, BaseRoleResponseFormat
from typing import Optional, Dict, List
from cola.utils.datatype import WorkflowEvent, RoleType
from cola.utils.agent_utils import RegisterAgent
from cola.utils.data_utils import PrivateData
from pydantic import BaseModel, Field
from config.config import Config
from cola.tools.controller.screenshot import Photographer
from cola.tools.controller.inspector import WindowsApplicationInspector
from cola.prompt.role.file_manager_prompt import FileManagerPrompt

config = Config.get_instance()
wai = WindowsApplicationInspector()
capturer = Photographer()

_rf_params = dict(
    role=RoleType.FileManager,
    additional_branch_type=None,
    additional_branch_desc=None,
)

FileManagerResponseFormat = BaseRoleResponseFormat(**_rf_params)


# class FileManagerResponseFormat(BaseRoleResponseFormat(**_rf_params)):
#     # selected_control: Optional[str] = Field(
#     #     ...,
#     #     description="The label of the chosen control for the operation."
#     #                 " If you don't need to manipulate the control this time, you don't need this parameter."
#     # )


@RegisterAgent(ignore_capability=False)
class FileManager(BaseRole):
    role = RoleType.FileManager
    capability = "Can open, create, and delete files, such as txt, xlsx, pdf, png, mp4 and other documents. Cannot do any other tasks beyond that."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.prompter: FileManagerPrompt = FileManagerPrompt()
        self.session_step = {
            "Execute Steps": [],
            "Experience": []
        }

    def branch_step(self, response: Dict, data: Optional[PrivateData] = None, **kwargs) -> PrivateData:
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
                message=response["message"],
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
        if not handoff:
            if "role_tasks" in data:
                self.cdc.summary_context[self.role].role_tasks = data.role_tasks

            self.episodic_messages = [
                self.prompter.create_system_prompt(FileManagerResponseFormat, self.role),
                *self.retrieve_long_term_memory(self.generate_summary())
            ]
            self.linked_messages = self.retrieve_short_term_memory()
            self.query_messages = [
                self.prompter.create_step_user_prompt(data)
            ]

            origin_response, response = self.query(format_model=FileManagerResponseFormat)
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

        if "result" in data:
            self.cdc.role_context.file_content = data.result
            self.cdc.role_context.pop("result")

        self.store_short_term_memory({
            "Intend": response["intention"],
            "Plan": response["local_plan"],
            "Summary": response["summary"]
        })

        return self.branch_step(response, data=data)
