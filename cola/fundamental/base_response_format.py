from pydantic import BaseModel, Field, create_model
from enum import StrEnum, Enum
from typing import Optional, List, Dict, Type
from cola.tools.op import OpType
from cola.utils.datatype import RoleType
from config.config import Config

config = Config.get_instance()


def BranchType(mode: str = "base", additional_branch_type: Optional[List[str]] = None,
               interact_mode: str = None) -> Type[Enum]:
    base_branch_type = ["Continue"]
    base_role_branch_type = ["Continue", "RoleTaskFinish", "TaskMismatch"]

    if mode == "base":
        branch_type = base_branch_type
    elif mode == "role":
        branch_type = base_role_branch_type
    else:
        raise ValueError(f"Unknown mode: {mode}, expected 'base' or 'role'.")

    if additional_branch_type:
        branch_type.extend(additional_branch_type)

    # add the branch type of requesting help when the interact_mode is passive
    if interact_mode == "passive":
        branch_type.append("NeedHumanHelp")
    # add the branch type of interrupt when the interact_mode is non-interactive
    elif interact_mode == "non-interactive":
        branch_type.append("Interrupt")
    else:
        raise ValueError(f"Unsupported interact_mode: `{interact_mode}`, expected 'passive' or 'non-interactive'.")

    branch_type = [(branch, branch) for branch in branch_type]
    return StrEnum("BranchType", branch_type, module=__name__)


def BranchDescription(enum_model: Type[Enum], additional_branch_desc: Optional[Dict[str, str]] = None,
                      interact_mode: str = None):
    branch_description = {
        "Continue": "Set to `Continue` when normal response processing of the task is underway, so that the next action can be performed.",
        "RoleTaskFinish": "Set to `RoleTaskFinish` when all the assigned subtasks are complete, so that the other subtasks can be executed.",
        "TaskMismatch": "set to `TaskMismatch` when you have been assigned a subtask that exceeds your capacity, so that you can reassign the subtask.",
        "NeedHumanHelp": "set to `NeedHumanHelp` when you are in trouble. Try not to ask humans for help unless necessary.",
        "Interrupt": "set to `Interrupt` when you really don't know what to do with a task. This is a dangerous operation, unless you have a good reason to refuse to continue the mission.",
    }
    if additional_branch_desc:
        branch_description.update(additional_branch_desc)

    desc = "The following are the values that can be set for this parameter and their explanations:"
    for branch in enum_model:
        desc += f" {branch_description[branch]}"
    return desc


_description = {
    "problem": "The problems you encountered. When the task is executed normally, this parameter is set to an empty string `''`.",
    "message": "The information you want to tell the next agent. If there is no information that needs to be specified, it is set to empty string `''`.",
    "summary": "Summarize the conversation. Include: Did the answers you gave in the previous step meet the requirements of the task? What have you done now? Why are you doing this?",
    "thought_process": "Give your thought process on the question, please step by step. Give a complete thought process.",
    "local_plan": "Give more detailed execution steps based on your historical experience and current scenarios and subtasks.",
    "intention": "What is your intention of this step, that is, the purpose of choosing this `operation`.",
    "operation": "You choose to perform the operation and its parameters. If you don't need to perform the operation, set it to empty.",
}


def _response_format(role: RoleType, mode: str, additional_branch_type: Optional[List[str]] = None,
                     additional_branch_desc: Optional[Dict[str, str]] = None,
                     interact_mode: str = None) -> Type[BaseModel]:
    branch_type = BranchType(mode, additional_branch_type, interact_mode)
    branch_desc = BranchDescription(branch_type, additional_branch_desc, interact_mode)

    base_params = dict(
        branch=(Optional[branch_type], Field(..., description=branch_desc)),
        problem=(str, Field(..., description=_description["problem"])),
        message=(str, Field(..., description=_description["message"])),
        summary=(str, Field(..., description=_description["summary"])),
    )

    if mode == "role":
        base_params = dict(
            thought_process=(List[str], Field(..., description=_description["thought_process"])),
            local_plan=(List[str], Field(..., description=_description["local_plan"])),
            intention=(str, Field(..., description=_description["intention"])),
            operation=(Optional[OpType(role)], Field(..., description=_description["operation"])),
            **base_params
        )

    model = create_model(
        "BaseResponseFormat" if mode == "base" else "BaseRoleResponseFormat",
        **base_params,
    )
    return model


def BaseResponseFormat(role: RoleType, additional_branch_type: Optional[List[str]] = None,
                       additional_branch_desc: Optional[Dict[str, str]] = None) -> Type[BaseModel]:
    interact_mode = "non-interactive"
    if config["interact_mode"] == "passive":
        interact_mode = "passive"
    return _response_format(role, "base", additional_branch_type, additional_branch_desc, interact_mode)


def BaseRoleResponseFormat(role: RoleType, additional_branch_type: Optional[List[str]] = None,
                           additional_branch_desc: Optional[Dict[str, str]] = None) -> Type[BaseModel]:
    interact_mode = "non-interactive"
    if config["interact_mode"] == "passive":
        interact_mode = "passive"
    return _response_format(role, "role", additional_branch_type, additional_branch_desc, interact_mode)
