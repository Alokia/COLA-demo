from cola.fundamental import BaseWorkflow, BaseRole
from cola.utils.datatype import WorkflowEvent, RoleType
from typing import Dict, Union
from cola.utils.print_utils import format_print_dict, print_with_color
from config.config import Config
from cola.utils.data_utils import PrivateData, ContextualDataCenter

config = Config.get_instance()
cdc = ContextualDataCenter()


class Workflow(BaseWorkflow):
    def __init__(self, all_agents: Dict[str, BaseRole]):
        super().__init__()
        self.all_agents = all_agents
        self.handoff = False

    @staticmethod
    def get_receiver(data: PrivateData):
        if "receiver" not in data:
            raise ValueError(f"receiver is not in data. {data}")
        if not RoleType.contains(data["receiver"]):
            raise ValueError(f"receiver `{data['receiver']}` is not in roles.")
        return data["receiver"]

    @staticmethod
    def get_event(data: PrivateData):
        if "event" not in data:
            raise ValueError(f"event is not in data. {data}")
        if not WorkflowEvent.contains(data["event"]):
            raise ValueError(f"event `{data['event']}` is not in WorkflowEvent.")
        return data["event"]

    def specify_role(self, role: RoleType, event: WorkflowEvent,
                     data: PrivateData = None,
                     handoff: bool = False, **kwargs):
        return self.all_agents[role].step(event=event, data=data, handoff=handoff, **kwargs)

    def next_step(self, data: PrivateData):
        role = self.get_receiver(data)
        event = self.get_event(data)
        handoff = self.handoff
        if self.handoff:
            self.handoff = False
        return self.specify_role(role=role, event=event, data=data, handoff=handoff)

    def step(self, data: PrivateData = None):
        while True:
            # 1. process cycle
            data = self.next_step(data)
            if data is None and cdc.switch_to is not None:
                data = cdc.get_context(cdc.switch_to)
                if data is None:
                    raise ValueError(
                        f"Switching role `{cdc.switch_to}` has no context. Please jump after a role has performed a task.")
                cdc.switch_to = None
                self.handoff = True
            format_print_dict(data)
            event = self.get_event(data)
            # 2. If it is a task that cannot be completed, terminate the run
            if event == WorkflowEvent.Interactor_task_failure:
                # TODO: Add Task Failure Handling
                print("task failure!", data)
                break
            # 3. Returns the result if it is a task completion
            elif event == WorkflowEvent.Interactor_task_accomplished:
                return data.answer
        return ""
