from cola.fundamental import BaseRole
from cola.utils.datatype import RoleType, WorkflowEvent
from cola.utils.agent_utils import RegisterAgent
from cola.utils.data_utils import PrivateData
from cola.tools.controller.inspector import WindowsApplicationInspector
from cola.tools.op import verify_op_params, role_op
from cola.tools.controller.screenshot import Photographer
import time

wai = WindowsApplicationInspector()
capturer = Photographer()


@RegisterAgent(ignore_capability=True)
class Executor(BaseRole):
    role = RoleType.Executor
    capability = "Performs mouse and keyboard actions and executes code and other operations."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def handle_store_memory(self, **kwargs):
        return

    @BaseRole.register_event(WorkflowEvent.Executor_execute_op)
    def handle_execute_op(self, data: PrivateData, **kwargs) -> PrivateData:
        """
        excepted keys:
            - sender
            - target_window
            - target_control
            - operation
            - intend
            - handle_event
            - not_track
        """
        role = data.sender
        target_window = None if "target_window" not in data else data.target_window
        target_control = None if "target_control" not in data else data.target_control
        track = True if "not_track" not in data else False
        if "operation" not in data or not data.operation:
            return PrivateData(
                sender=self.role, receiver=role, event=data.handle_event,
                feedback="The operation is not specified, please check the operation.",
            )
        function = data["operation"]["function"]
        params = data["operation"]["params"]
        try:
            # All ops use the json schema format for parameter validation, so there is no need to manually validate the parameters here
            # verify_op_params(function, role, operations=None, ignore_params=None, **params)
            track_before_state = None if not track else capturer.take_desktop_screenshot()
            result = role_op[role][function](target_window, target_control, **params)
            time.sleep(5)  # Pause to ensure that the effect of the action is executed
            track_after_state = None if not track else capturer.take_desktop_screenshot()

            self.cdc.role_context.result = result
            return PrivateData(
                sender=self.role, receiver=RoleType.Reviewer, event=WorkflowEvent.Reviewer_track_state,
                track_before_state=track_before_state, track_after_state=track_after_state,
                execute_op=function, mandator=role, result=result, handle_event=data.handle_event,
                intend=data.intend
            )
        except ValueError as e:
            return PrivateData(
                sender=self.role, receiver=role, event=data["handle_event"],
                feedback="Executor: the operation failed to execute, please check the operation."
                         " This is the error: \n{}".format(str(e))
            )
