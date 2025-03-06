from cola.utils.datatype import WorkflowEvent, RoleType
from cola.utils.json_utils import extract_json_from_response
from cola.utils.print_utils import any_to_str, print_with_color
from cola.utils.data_utils import PrivateData, ContextualDataCenter
from cola.utils.error_utils import LMResponseFormatError, MaxQueryTimesError, MaxRetryTimesError
from cola.fundamental.base_lm import BaseLM
from cola.fundamental.singleton import Singleton
from cola.fundamental.base_memory import BaseMemory
from cola.fundamental.base_prompt import BasePrompt
from typing import Dict, Optional, List, Type, Tuple, Union, Callable, Any
import os
import json
from abc import ABC
from pydantic import ValidationError, BaseModel
from config.config import Config
from logger.logger import ChatMessageLogger

cm_logger = ChatMessageLogger()
config = Config.get_instance()


class MemoryMechanism:
    lt_memory_store: Optional[BaseMemory] = None  # long-term memory store
    st_memory_store: Optional[BaseMemory] = None  # short-term memory store
    n_chat_message_history: int = 2  # number of long-term memory history
    n_short_message_history: int = 5  # number of short-term memory history
    session_step: Dict[str, List] = None  # record the whole session

    def __init__(self, **kwargs):
        pass

    def record_session_step(self, step: Dict = None, exp: str = None, **kwargs):
        """Records the session execution steps for subsequent retrieval.

        Parameter:
            step: Dict, Execute Steps, documented in the Execute Steps step
            exp: str, Experience, recorded in the Experience step
        """
        if step is not None:
            self.session_step["Execute Steps"].append(step)
        if exp is not None:
            self.session_step["Experience"].append(exp)

    def retrieve_long_term_memory(self, desc: Any) -> List[Dict[str, Union[str, List[Dict]]]]:
        """
        Retrieving historical messages from long-term memory

        Parameter:
            desc: str, Description of the search

        Return:
            List[Dict[str, str]], Historical Messages.
            If the history message is empty, the empty list is returned
        """

        def _get_content(_his: List):
            _task_content = "Task: " + _his[0]["Task"]
            _step_content = []
            for _i, _s in enumerate(_his[1:]):
                _step_content.append(f"(step {_i + 1})\n" + "```json\n" + json.dumps(_s, indent=4) + "\n```")
            _step_content = "Execution Steps:\n" + "\n".join(_step_content)
            return _task_content + "\n" + _step_content

        desc = any_to_str(desc)

        messages: List[Dict[str, str]] = []
        # Retrieve history from database
        if self.lt_memory_store is not None:
            history: List[List] = self.lt_memory_store.similarity_search(
                text=desc, k=self.n_chat_message_history)
            # Reverse the history operations so that the history operation with the highest similarity is the last
            history = history[::-1]

            content = []
            for i, h in enumerate(history):
                content.append(f"[Example {i + 1}]\n" + _get_content(h))
            content = "\n".join(content)
            messages = [{"role": "system", "content": content}]

        return messages

    def store_long_term_memory(self, summary: Any,
                               session_id: Optional[str] = None,
                               mode: str = "cw") -> None:
        """
        Storing historical messages in long-term memory for subsequent retrieval

        Parameter:
            summary: str, Summary of the message
            session_id: Optional[str], Session ID, specify the stored session ID, if None, a new ID is generated
            mode: str, Storage Mode
        """
        if self.session_step is None or len(self.session_step["Execute Steps"]) == 0:
            return
        summary = any_to_str(summary)
        if self.lt_memory_store is None:
            return
        # 简单存储记录的执行步骤
        store_messages = [{"Task": summary}] + self.session_step["Execute Steps"]
        self.lt_memory_store.add(session_id=session_id, summary=summary, messages=store_messages, mode=mode)

    def retrieve_short_term_memory(self) -> List[Dict[str, str]]:
        """
        Retrieving messages from short-term memory

        Return:
            List[Dict[str, str]], Historical Messages.
        """
        messages = []
        if self.st_memory_store is not None:
            history: List[Dict] = self.st_memory_store.similarity_search(k=self.n_short_message_history)
            for n, h in enumerate(history):
                msg = f"[Article {n + 1} Recent records]"
                for k, v in h.items():
                    v_str = any_to_str(v)
                    msg += f"\n{k}: {v_str}"
                messages.append(msg)
        if len(messages) != 0:
            content = "The following is a record of the most recent tasks performed. Consider how these execution records relate to the current task and draw on these experiences to complete the new task.\n"
            content += '\n'.join(messages)
            messages = [{"role": "system", "content": content}]
        return messages

    def store_short_term_memory(self, messages: Union[List[Dict], Dict]) -> None:
        """
        Storing messages into short-term memory

        Parameter:
            messages: Union[List[Dict], Dict], Short-term memory information to be stored
        """
        if self.st_memory_store is None:
            return
        self.st_memory_store.add(messages=messages)


class BrainMechanism:
    brain: BaseLM = None  # LM
    prompter: BasePrompt = None  # prompter for generating prompt messages
    interact_mode: str = None  # Interaction mode for Role
    max_retry_times: int = 3  # Maximum number of retries
    max_query_times: int = 20  # Maximum number of requests
    role: RoleType = None  # Role played by cola, such as planner, executor, evaluator, etc.
    agents_capability: Dict[str, str] = None  # Description of the agent's capabilities
    cdc: ContextualDataCenter = None  # Data Center for Recording Context

    def __init__(self, **kwargs):
        # A complete request is episodic_messages + linked_messages + query_messages + tip_messages
        # Used to store historical messages retrieved from long-term memory
        self.episodic_messages = []
        # Used to store messages retrieved from short-term memory
        self.linked_messages = []
        # Used to store one-time request messages
        self.query_messages = []
        # Used to store error correction information in case of formatting errors, this message list is handled transparently without logging and external operations.
        self.tip_messages = []
        # Number of logging requests
        self.request_times = 0
        # Record all Q/R messages for the current task
        self.session_messages = []

    def extract_json(self, response: str, verify: bool = True,
                     format_model: Type[BaseModel] = None, **kwargs) -> Dict:
        """
        Extract the json data from the LM's response and verify that it is formatted correctly

        Parameter:
            response: str, LM's original response
            verify: bool, Whether the format needs to be validated
            format_model: Type[pydantic.BaseModel], Modeling of validation formats

        Return:
            Dict, Extracted json data

        Raise:
            LMResponseFormatError: Throws an exception when the response is not formatted correctly, the exception contains an error message and can be used for error correction.
        """
        try:
            data = extract_json_from_response(response)
        except ValueError as e:
            # If the json extraction fails, add an error response in tip_messages
            self.tip_messages.append(self.prompter.create_ai_prompt(response))
            # Throws LMResponseFormatError, the exception message is a hint for error correction, which can be added to tip_messages for error correction
            feedback = ""
            if format_model is not None:
                feedback += "The expected json parameter format is\n" + "```json\n" + self.prompter.format_description(
                    format_model) + "\n```\n"
            feedback += "The output is incorrectly formatted, please make corrections based on the feedback below to regenerate the correct answer.\n"
            feedback += f"Error details: {e}\n"
            feedback += "Please regenerate the correct reply based on this feedback and historical messages. Take a deep thought and give your reply: \n"
            raise LMResponseFormatError(feedback)
        if verify:
            assert format_model is not None, f"{self.__class__}: format_model is None, please provide a format_model."
            try:
                data = format_model(**data)
                return data.model_dump()
            except ValidationError as e:
                # If the json key is incorrect, add a response to the error in tip_messages
                self.tip_messages.append(self.prompter.create_ai_prompt(response))
                feedback = "The expected json parameter format is\n" + "```json\n" + self.prompter.format_description(
                    format_model) + "\n```"
                feedback += "\nThe output is incorrectly formatted, please make corrections based on the feedback below to regenerate the correct answer."
                feedback += "\nError details: "
                for error in e.errors():
                    feedback += f"\n{error['loc'][0]}: {error['msg']}"
                feedback += "\nPlease regenerate the correct reply based on this feedback and historical messages. Take a deep thought and give your reply: "
                raise LMResponseFormatError(feedback)
        return data

    def query(self, query_messages: List[Dict[str, str]] = None,
              episodic_messages: List[Dict[str, str]] = None,
              linked_messages: List[Dict[str, str]] = None,
              verify: bool = True,
              use_openai_format: bool = True,
              format_model: Type[BaseModel] = None,
              extract_json: bool = True,
              **kwargs) -> Tuple[str, Dict]:
        """The query method with error handling, see _query() for arguments.
        """
        # Record the number of requests and terminate the program when the number of requests reaches a preset upper limit
        self.request_times += 1
        if self.request_times >= self.max_query_times:
            raise MaxQueryTimesError(
                "{} has reached the maximum number of requests. Request times: {}".format(self.role, self.request_times)
            )

        # If max_retry_times is None, or if openai json format support is used, or if extract_json is not performed, then no retries are performed
        if ((self.max_retry_times is None) or
                (use_openai_format and format_model is not None) or
                (not extract_json)):
            return self._query(
                query_messages, episodic_messages, linked_messages, verify,
                use_openai_format, format_model, extract_json, **kwargs
            )
        # Otherwise, retry
        retry_times = 0
        while retry_times <= self.max_retry_times:
            try:
                return self._query(
                    query_messages, episodic_messages, linked_messages, verify,
                    use_openai_format, format_model, extract_json, **kwargs
                )
            except LMResponseFormatError as e:
                self.tip_messages.append(self.prompter.create_user_prompt(str(e)))
                retry_times += 1
        # If the number of retries exceeds the maximum number of retries, an exception is thrown
        raise MaxRetryTimesError(
            f"LM response was formatted incorrectly and the maximum number of retries has been reached. Retry times: {self.max_retry_times}"
        )

    def _query(self, query_messages: List[Dict[str, str]] = None,
               episodic_messages: List[Dict[str, str]] = None,
               linked_messages: List[Dict[str, str]] = None,
               verify: bool = True,
               use_openai_format: bool = True,
               format_model: Type[BaseModel] = None,
               extract_json: bool = True,
               func_branch: Optional[str] = None,
               **kwargs) -> Tuple[str, Dict]:
        """
        Sends a request to the LM and handles the LM's response

        Parameter:
            query_messages: List[Dict[str, str]], Request message for the current task
            episodic_messages: List[Dict[str, str]], Messages containing system templates and historical memory
            linked_messages: List[Dict[str, str]], News from short-term memory
            verify: bool, Whether the format needs to be validated, see extract_json()
            use_openai_format: bool, Whether to use openai's json format support
            format_model: Type[pydantic.BaseModel], Validate the model of the format, see extract_json()
            extract_json: bool, Whether to extract json data
            func_branch: Optional[str], Used to mark what the function is called by, optionally “Error correction”, “Human Feedback”.

        Return:
            Tuple[str, Dict], Raw response and extracted json data, if extract_json is False, then return an empty dictionary.
        """
        assert self.brain is not None, f"{self.__class__} - brain is None. Please check if the brain is initialized."

        if episodic_messages is None:
            episodic_messages = self.episodic_messages
        if linked_messages is None:
            linked_messages = self.linked_messages
        if query_messages is None:
            query_messages = self.query_messages

        # Get the original response from LM
        origin_response = self.brain.query(
            episodic_messages + linked_messages + query_messages + self.tip_messages,
            response_format=format_model if use_openai_format else None
        )
        if use_openai_format and (format_model is not None):
            response = origin_response.dict()
            origin_response = "```json\n" + json.dumps(response, indent=4) + "\n```"
        else:
            response = {}
            if extract_json:
                response = self.extract_json(origin_response, verify=verify, format_model=format_model)

        # The fact that we have reached this point means that the response has been obtained correctly, so clear the tip_messages to avoid introducing useless information.
        self.tip_messages.clear()
        # Store logs, error correction mechanisms are transparent and not logged
        query_messages.append(self.prompter.create_ai_prompt(origin_response))
        cm_logger.log(
            episodic_messages + linked_messages + query_messages,
            role=self.role
        )
        # Record Q/R messages for the current task
        # TODO: When the Human Feedback is executed, whether the Q/R message of the current task needs to be recorded or not, the parameter func_branch is empty.
        if func_branch is None:
            self.session_messages.extend(query_messages)

        _params = dict(
            episodic_messages=episodic_messages, linked_messages=linked_messages, verify=verify,
            use_openai_format=use_openai_format, format_model=format_model, extract_json=extract_json,
            func_branch=func_branch
        )
        self.cdc.set_query_params(self.role, (query_messages, _params))

        # Handle manual feedback branches, process them here to avoid context and parameter loss
        if (response and ("branch" in response) and (response["branch"] == "NeedHumanHelp")) or (
                self.interact_mode == "proactive"):
            _origin_response, _response = self.human_feedback_step(
                False, origin_response, query_messages, **_params
            )
            if _origin_response == "skip" and _response == "skip":
                return origin_response, response
            return _origin_response, _response

        return origin_response, response

    def human_feedback_step(self, handoff: bool, response: str = None, query_messages: List[Dict] = None, **kwargs):
        """Handle manual feedback. The method may need to be rewritten to accommodate different role requirements.

        By default, this method is called automatically in _query(), make sure that the output json contains the `branch` parameter and only call this method if it is `NeedHumanHelp`.
        """
        # If human_feedback_step was called by handoff, the last response is printed.
        if handoff:
            print_with_color(f"Switch to `{self.role}`. Last Response is follow:", "blue")
            print(self.query_messages[-1]["content"])
            print_with_color(f"{self.role} has been answered, please give guidance: ", "red")
        else:
            if self.interact_mode == "proactive":
                print_with_color(f"{self.role} has been answered, please give guidance: ", "red")
            else:
                print_with_color(f"{self.role} have encountered some problems, please give some advice: ", "red")

        # Open the recorded markdown file to facilitate human observation of the requested information and advise accordingly
        if config["open_markdown_for_human_feedback"]:
            os.startfile(cm_logger.role_last_md_path[self.role])
        feedback = input("Please input feedback (Enter 'skip' or 'switch to ***' to perform special operations): \n")
        if feedback == "skip":
            return "skip", "skip"
        if query_messages is None:
            query_messages = self.query_messages

        # handoff branch
        if self.handoff_step(feedback):
            return None, None

        query_messages.append(self.prompter.create_user_prompt([
            "This is the guidance given by human beings:",
            "{}".format(feedback),
            "Please follow these recommendations to implement the mandate."
        ]))

        return self._query(query_messages=query_messages, **kwargs)

    def handoff_step(self, feedback: str) -> bool:
        # response = get_handoff_response(self.brain, feedback)
        # print_with_color(
        #     response["analyze"] + (
        #         "" if response["branch"] == "No" else (
        #                 "\nSwitching Role To: " + response["role"])), "green")
        # if response["branch"] == "Yes":
        #     self.cdc.switch_to = response["role"]
        #     return True
        # return False
        if feedback.startswith("switch to"):
            self.cdc.switch_to = feedback.split(" ")[-1]
            return True
        return False


class BaseRole(ABC, MemoryMechanism, BrainMechanism, metaclass=Singleton):
    role: RoleType = None
    capability: str = None

    def __init__(self, lm: BaseLM = None,
                 agents_capability: Dict[str, str] = None,
                 long_term_memory_store: Optional[BaseMemory] = None,
                 short_term_memory_store: Optional[BaseMemory] = None,
                 n_chat_message_history: int = 2,
                 n_short_message_history: int = 5,
                 max_retry_times: int = 3,
                 max_query_times: int = 20,
                 interact_mode: str = None, ):
        self.handle = {}  # Used to store all functions with the _event attribute as event: function
        self._register_all_event()

        MemoryMechanism.__init__(self)
        BrainMechanism.__init__(self)

        self.brain = lm

        self.lt_memory_store = long_term_memory_store
        self.st_memory_store = short_term_memory_store
        self.n_chat_message_history = n_chat_message_history
        self.n_short_message_history = n_short_message_history

        self.max_retry_times = max_retry_times
        self.max_query_times = max_query_times

        self.agents_capability = agents_capability
        self.interact_mode = interact_mode

        self.cdc = ContextualDataCenter()

    def has_event(self, event: WorkflowEvent) -> bool:
        return event in self.handle

    @staticmethod
    def register_event(event: WorkflowEvent):
        """
        Add the _event attribute to the function to mark the event, register all functions with the event via the register() method,
        and all results will be stored in the handle as event: function, which will be called via the step() method.
        """

        def wrapper(func):
            func._event = event
            return func

        return wrapper

    def _register_all_event(self):
        """Register all functions with the _event attribute, stored in handle"""
        for method in dir(self):
            if not method.startswith("__") and callable(getattr(self, method)):
                func = getattr(self, method)
                if hasattr(func, "_event"):
                    self.handle[func._event] = func

    def generate_summary(self):
        task = self.cdc.session_context.task
        if "role_tasks" in self.cdc.summary_context[self.role] and self.cdc.summary_context[self.role].role_tasks:
            summary = "Role Task: " + any_to_str(
                self.cdc.summary_context[self.role].role_tasks) + "\nTotal Task: " + task
        elif "sub_tasks" in self.cdc.summary_context[self.role] and self.cdc.summary_context[self.role].sub_tasks:
            summary = "Sub Task: " + any_to_str(
                self.cdc.summary_context[self.role].sub_tasks) + "\nTotal Task: " + task
        else:
            summary = task
        return summary

    def handle_store_memory(self, session_id: Optional[str] = None,
                            summary: Any = None,
                            mode: str = "cw"):
        if summary is None:
            summary = self.generate_summary()
        if session_id is None and config["session_id"]:
            session_id = config["session_id"]
        if summary is not None:
            self.store_long_term_memory(
                summary=summary, session_id=session_id, mode=mode,
            )

    def branch_step(self, response: Dict, **kwargs) -> PrivateData:
        return PrivateData(**response)

    def handoff_query(self):
        query_messages, params = self.cdc.get_query_params(self.role)
        origin_response, response = self.human_feedback_step(True, None, query_messages, **params)
        return origin_response, response

    def step(self, event: WorkflowEvent = None, data: PrivateData = None,
             handoff: bool = False, **kwargs) -> Optional[PrivateData]:
        if not handoff:
            data = self.cdc.prepare_data(self.role, data)
            self.cdc.set_context(self.role, data)  # save context to cdc session record space

        if event is None:
            event = data.event
            if not WorkflowEvent.contains(event):
                raise ValueError(f"event {event} is not in {WorkflowEvent.to_str()}.")
        if data is None and kwargs is None:
            raise ValueError("data and kwargs is None.")
        if not self.has_event(event):
            raise ValueError(f"event {event} is not handled in `{self.role}`.")

        step_data: Optional[PrivateData] = self.handle[event](data=data, handoff=handoff, **kwargs)
        if step_data:
            cm_logger.log_data(step_data, "data")
        return step_data
