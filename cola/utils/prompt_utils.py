from functools import wraps
from typing import List
from cola.utils.print_utils import any_to_str
from cola.utils.data_utils import PrivateData


class RegisterCatcher:
    def __init__(self, params: List[str] | str):
        self.params = params
        if isinstance(self.params, str):
            self.params = [self.params]

    def verify(self, data: PrivateData) -> bool:
        for param in self.params:
            if param not in data or not data[param]:
                return False
        return True

    def __call__(self, func):
        @wraps(func)
        def wrapper(data: PrivateData) -> List[str]:
            content = []
            if self.verify(data):
                content = func(data)
            return content

        return wrapper


@RegisterCatcher(["message", "sender"])
def catch_message(data: PrivateData) -> List[str]:
    content = [
        "This is the message from {}: {}".format(data.sender, data.message),
    ]
    return content


@RegisterCatcher(["result"])
def catch_result(data: PrivateData) -> List[str]:
    content = [
        "This is the result from the previous step: \n",
        any_to_str(data.result),
        "Make sure that this result is what is needed, if it is and the current task has been completed in full, then you can set branch to `RoleTaskFinish`."
    ]
    return content


@RegisterCatcher(["feedback", "sender"])
def catch_feedback(data: PrivateData) -> List[str]:
    content = [
        "This is the feedback from the {}: \n  {}".format(data.sender, data.feedback),
    ]
    return content


catches = {
    "message": catch_message,
    "result": catch_result,
    "feedback": catch_feedback
}