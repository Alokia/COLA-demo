from cola.fundamental import BaseRole, BaseResponseFormat
from typing import Optional, Dict
from cola.utils.datatype import WorkflowEvent, RoleType
from cola.prompt.reviewer_prompt import ReviewerPrompt
from cola.utils.data_utils import PrivateData
from cola.utils.agent_utils import RegisterAgent
from cola.tools.controller.screenshot import Photographer
from pydantic import BaseModel, Field

capturer = Photographer()

_rf_params = dict(
    role=RoleType.Reviewer,
    additional_branch_type=None,
    additional_branch_desc=None,
)


class ReviewerResponseFormat(BaseResponseFormat(**_rf_params)):
    analyze: str = Field(
        ...,
        description="Give your process for analyzing the scenario."
    )
    judgement: str = Field(
        ...,
        description="Give your judgment as to whether the action accomplishes the intent."
    )


@RegisterAgent(ignore_capability=True)
class Reviewer(BaseRole):
    role = RoleType.Reviewer
    capability = "Tracks changes in the state of the computer desktop and determines if the action meets expectations"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.prompter: ReviewerPrompt = ReviewerPrompt()

        self.session_step = {
            "Execute Steps": [],
            "Experience": []
        }

        self._track_execute_op = None
        self._track_intend = None

    def generate_summary(self):
        if self._track_execute_op and self._track_intend:
            return self._track_execute_op + ": " + self._track_intend
        elif self._track_execute_op is None and self._track_intend:
            return self._track_intend
        else:
            return self.cdc.session_context.task

    def branch_step(self, response: Dict, data: Optional[PrivateData] = None, **kwargs) -> PrivateData:
        if (branch := response["branch"]) == "Continue":
            return PrivateData(
                sender=self.role, receiver=data.mandator, event=data.handle_event,
                feedback=response["judgement"], message=response["message"],
            )
        else:
            raise ValueError(f"Unknown branch type: {branch} in {self.role}")

    @BaseRole.register_event(WorkflowEvent.Reviewer_track_state)
    def handle_track_state(self, data: PrivateData, handoff: bool, **kwargs) -> Optional[PrivateData]:
        """
        excepted keys:
            - mandator
            - handle_event
            - result
            - track_before_state
            - track_after_state
            - intend
            - execute_op
            - message
        """
        if not handoff:
            self._track_execute_op = data.execute_op
            self._track_intend = data.intend

            self.episodic_messages = [
                self.prompter.create_system_prompt(ReviewerResponseFormat),
                *self.retrieve_long_term_memory(self.generate_summary()),
            ]
            self.linked_messages = self.retrieve_short_term_memory()
            self.query_messages = [
                self.prompter.create_track_state_user_prompt(data)
            ]

            origin_response, response = self.query(format_model=ReviewerResponseFormat)
            if origin_response is None and response is None and self.cdc.switch_to is not None:
                return None
        else:
            origin_response, response = self.handoff_query()

        # record execution steps
        self.record_session_step(step=dict(
            judgement=response["judgement"], branch=response["branch"]
        ))

        self.store_short_term_memory({
            "Role": data.mandator,
            "Execute Operation": data.execute_op,
            "Intend": data.intend,
            "Analyze": response["analyze"],
            "Judgement": response["judgement"],
            "Summary": response["summary"]
        })

        return self.branch_step(response, data=data)
