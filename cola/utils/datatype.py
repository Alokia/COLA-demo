from enum import StrEnum


class BaseDataClass(StrEnum):
    @classmethod
    def data_list(cls):
        return [getattr(cls, attr) for attr in dir(cls) if
                not attr.startswith("__") and not callable(getattr(cls, attr))
                and isinstance(attr, str)]

    @classmethod
    def to_str(cls):
        return f"{cls.__name__}({', '.join([f'{attr}' for attr in cls.data_list()])})"

    @classmethod
    def contains(cls, item: str):
        return item in cls.data_list()


class WorkflowEvent(BaseDataClass):
    task_accomplished = "task_accomplished"
    task_interrupt = "task_interrupt"
    task_resumption = "task_resumption"
    task_failure = "task_failure"
    after_task_accomplished = "after_task_accomplished"

    Interactor_start_task = "Interactor_start_task"
    Interactor_task_failure = "Interactor_task_failure"
    Interactor_task_accomplished = "Interactor_task_accomplished"

    Planner_make_sub_task = "Planner_make_sub_task"

    TaskScheduler_distribute_subtask = "TaskScheduler_distribute_subtask"
    TaskScheduler_distribute_next_subtask = "TaskScheduler_distribute_next_subtask"

    Executor_execute_op = "Executor_execute_op"

    Reviewer_track_state = "Reviewer_track_state"

    Role_step = "Role_step"


class RoleType(BaseDataClass):
    Human = "Human"
    Interactor = "Interactor"

    Planner = "Planner"
    TaskScheduler = "TaskScheduler"
    Executor = "Executor"
    Reviewer = "Reviewer"

    Programmer = "Programmer"
    FileManager = "FileManager"
    Searcher = "Searcher"
    ApplicationManager = "ApplicationManager"


class RoleKey(StrEnum):
    sender = "sender"
    receiver = "receiver"
    event = "event"
    message = "message"
    result = "result"
    feedback = "feedback"
    target_window = "target_window"
    file_content = "file_content"
    role_infos = "role_infos"
