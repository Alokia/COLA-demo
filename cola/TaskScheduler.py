from cola.fundamental import BaseRole, BaseResponseFormat
from cola.utils.datatype import WorkflowEvent, RoleType
from cola.prompt.task_scheduler_prompt import TaskSchedulerPrompt
from typing import Any, Callable, List, Optional, Dict
from cola.utils.agent_utils import RegisterAgent
from cola.utils.data_utils import PrivateData
from pydantic import BaseModel, Field

_rf_params = dict(
    role=RoleType.TaskScheduler,
    additional_branch_type=["RemakeSubtasks"],
    additional_branch_desc=dict(
        RemakeSubtasks="set to `RemakeSubtasks` when the list of subtasks not suit the downstream role."
    )
)


class DistributionFormat(BaseModel):
    role: str = Field(
        ...,
        description="The role to process the subtasks"
    )
    role_tasks: List[str] = Field(
        ...,
        description="A list of subtasks that the specified role needs to process"
    )


class TaskSchedulerResponseFormat(BaseResponseFormat(**_rf_params)):
    distribution: List[DistributionFormat] = Field(
        ...,
        description="A list of subtasks that need to be processed by different roles. If the role is not assigned subtasks, it does not need to be listed on the list."
    )


@RegisterAgent(ignore_capability=True)
class TaskScheduler(BaseRole):
    role = RoleType.TaskScheduler
    capability = "Scheduling the execution of tasks based on the list of subtasks and downstream role capability descriptions."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.prompter: TaskSchedulerPrompt = TaskSchedulerPrompt(self.agents_capability)

        self.session_step = {
            "Execute Steps": [],
            "Experience": []
        }

        self.cdc.create_base_role_context_space(self.role)
        self.cdc.base_role_context[self.role].distribution = []
        self.cdc.base_role_context[self.role].distribution_id = 0

    def branch_step(self, response: Dict, data: Optional[PrivateData] = None, **kwargs) -> PrivateData:
        if (branch := response["branch"]) == "Continue":
            distribute_information = self.cdc.base_role_context[self.role].distribution[
                self.cdc.base_role_context[self.role].distribution_id]
            link_message = {
                "Performed action": "distribute a subtasks",
                "Distribute information": distribute_information
            }
            self.store_short_term_memory(link_message)

            self.cdc.role_context.role_tasks = distribute_information["role_tasks"]
            return PrivateData(
                sender=self.role, receiver=distribute_information["role"],
                event=WorkflowEvent.Role_step,
                role_tasks=distribute_information["role_tasks"]
            )
        elif branch == "RemakeSubtasks":
            return PrivateData(
                sender=self.role, receiver=RoleType.Planner,
                event=WorkflowEvent.Planner_make_sub_task,
                problem=response["problem"]
            )
        else:
            raise ValueError(f"Unknown branch type: {branch} in {self.role}")

    @BaseRole.register_event(WorkflowEvent.TaskScheduler_distribute_subtask)
    def handle_distribute_subtasks(self, data: PrivateData, handoff: bool, **kwargs) -> Optional[PrivateData]:
        """
        excepted keys:
            - sub_tasks
            - role_tasks
            - problem
            - message
        """
        if not handoff:
            if "sub_tasks" in data:
                self.cdc.summary_context[self.role].sub_tasks = data.sub_tasks

            self.episodic_messages = [
                self.prompter.create_system_prompt(TaskSchedulerResponseFormat),
                *self.retrieve_long_term_memory(self.generate_summary())
            ]
            self.linked_messages = self.retrieve_short_term_memory()
            self.query_messages = [
                self.prompter.create_distribute_subtasks_user_prompt(data)
            ]
            origin_response, response = self.query(format_model=TaskSchedulerResponseFormat)
            if origin_response is None and response is None and self.cdc.switch_to is not None:
                return None
        else:
            origin_response, response = self.handoff_query()

        # record execution steps
        self.record_session_step(step=dict(
            distribution=response["distribution"], branch=response["branch"]
        ))

        self.cdc.base_role_context[self.role].distribution = response["distribution"]
        self.cdc.base_role_context[self.role].distribution_id = 0

        self.store_short_term_memory({
            "Generated distribution": response["distribution"],
            "Summary": response["summary"]
        })

        return self.branch_step(response, data=data)

    @BaseRole.register_event(WorkflowEvent.TaskScheduler_distribute_next_subtask)
    def handle_distribute_next_subtask(self, data: PrivateData, **kwargs) -> PrivateData:
        """
        excepted keys:
        """
        self.cdc.base_role_context[self.role].distribution_id += 1
        if self.cdc.base_role_context[self.role].distribution_id >= len(
                self.cdc.base_role_context[self.role].distribution):
            return PrivateData(
                sender=self.role, receiver=RoleType.Planner,
                event=WorkflowEvent.task_accomplished,
                role_infos=self.cdc.role_context["role_infos"]
            )
        return self.branch_step(dict(branch="Continue"), data=data)
