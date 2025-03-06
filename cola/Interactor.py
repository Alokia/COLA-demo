from cola.fundamental import BaseRole
from cola.utils.datatype import WorkflowEvent, RoleType
from cola.utils.agent_utils import RegisterAgent
from cola.utils.data_utils import PrivateData


@RegisterAgent(ignore_capability=True)
class Interactor(BaseRole):
    role = RoleType.Interactor
    capability = "A bridge for interaction between human and agents"

    def __init__(self, agents_instance, **kwargs):
        super().__init__(**kwargs)
        self.agents_instance = agents_instance

    @BaseRole.register_event(WorkflowEvent.Interactor_start_task)
    def handle_start_task(self, data: PrivateData, **kwargs) -> PrivateData:
        self.cdc.session_context.task = data.task
        return PrivateData(
            sender=self.role, receiver=RoleType.Planner,
            event=WorkflowEvent.Planner_make_sub_task,
            task=data.task
        )

    @BaseRole.register_event(WorkflowEvent.task_accomplished)
    def handle_task_accomplished(self, data: PrivateData, **kwargs) -> PrivateData:
        # Send the handle_task_finish event to all cola's when the task is successful
        # for role, agent in self.agents_instance.items():
        #     if role != self.role and agent.has_event(WorkflowEvent.after_task_accomplished):
        #         agent.step(event=WorkflowEvent.after_task_accomplished)
        return PrivateData(
            sender=self.role, receiver=RoleType.Human, answer=data.answer,
            event=WorkflowEvent.Interactor_task_accomplished
        )

    def handle_store_memory(self, **kwargs):
        # for role, agent in self.agents_instance.items():
        #     if role != self.role:
        #         agent.handle_store_memory()
        return
