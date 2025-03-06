from typing import List, Callable, Type, Dict
from config.config import Config
import time
from functools import wraps
import inspect
from pywinauto.controls.uiawrapper import UIAWrapper
from copy import deepcopy
from pydantic import BaseModel
from cola.utils.print_utils import format_pydantic_model
from cola.utils.datatype import RoleType

config = Config.get_instance()

role_op: Dict[RoleType, Dict] = {}
role_op_model: Dict[RoleType, List] = {}
op_model_map: Dict[str, Type[BaseModel]] = {}
op_func_map: Dict[str, Callable] = {}


def verify_op_params(func_name: str,
                     role: RoleType,
                     operations: Dict = None,
                     ignore_params: List[str] = None,
                     **kwargs):
    if ignore_params is None:
        ignore_params = ["window", "control"]
    if operations is None:
        global role_op
        operations = role_op[role]

    if func_name not in operations:
        raise ValueError("Unsupported operation: {}. ".format(func_name) +
                         "Please select from the following operations: [{}]".format(", ".join(list(operations.keys()))))
    val_params = deepcopy(kwargs)
    args = operations[func_name].args

    for param_name, param_info in args.parameters.items():
        # If the parameter is not in the list of validation parameters and the parameter does not have a default value, an exception message is returned
        if param_name not in val_params:
            if param_name in ignore_params:
                continue
            elif param_info.default == param_info.empty:
                raise ValueError("Missing required parameter: `{}` in operation `{}`".format(param_name, func_name))
        # If the parameter is in the validation parameter list, but the parameter's value type does not match, an exception message is returned
        elif not isinstance(val_params[param_name], param_info.annotation):
            return ValueError(
                "Parameter type mismatch: `{}` should be {}".format(param_name, param_info.annotation))
        # If the parameter is in the validation parameter list and the parameter's value type matches, remove the parameter from the validation parameter list
        else:
            val_params.pop(param_name)

    if len(val_params) != 0:
        raise ValueError("Unsupported parameter: `{}` in operation `{}`".format(val_params, func_name))
    return True


def get_ops_description(role: RoleType = None, operations: Dict = None) -> str:
    """Get the description of the operations in the module

    Parameter:
        module: Any -- The module that contains the operations,
            every operation should be decorated with @OperationRegister
        operate_list: List[str] -- The list of operations to be described, if None, it will be module.__all__

    Return:
        str -- The description of the operations
    """
    if operations is None:
        global role_op
        operations = role_op[role]

    func_desc = []
    for func_name, func in operations.items():
        func_desc.append("- {} :".format(func.__name__) + "\n" + func.__doc__)
    return "\n".join(func_desc)


def get_ops_function_dict(operations: Dict = None) -> Dict:
    """Get the function of the operations"""
    if operations is None:
        global op_func_map
        operations = op_func_map

    func_desc = {}
    for func_name, func in operations.items():
        op_function = func.__doc__.split("\n")[0]
        func_desc[func_name] = op_function
    return func_desc


class OperationRegister:
    def __init__(self, model: Type[BaseModel], roles: List[RoleType], control_types: List[str] = None):
        global role_op_model

        self.roles = roles
        if roles is None:
            self.roles = RoleType.data_list()

        for role in self.roles:
            if role not in role_op_model:
                role_op_model[role] = []
            role_op_model[role].append(model)

        self.model = model

        self.control_types = control_types
        if control_types is None:
            self.control_types = config["control_list"]

    @staticmethod
    def wait_visible(control: UIAWrapper, timeout: float = 10, retry_interval: float = 0.5):
        while not control.is_visible():
            time.sleep(retry_interval)
            control.set_focus()
            timeout -= retry_interval
            if timeout <= 0:
                raise TimeoutError(f"Timeout to wait control visible: {control}")

    def __call__(self, func):
        func.__doc__ = str(func.__doc__).replace(
            "[Parameter]", format_pydantic_model(
                self.model,
                pattern=lambda x: x.replace("{", "").replace("}", "").replace("\\", "").strip("\n")
            ))

        @wraps(func)
        def wrapper(window: UIAWrapper, control: UIAWrapper, *args, **kwargs) -> Callable:
            # If the given control is null, the function is executed directly, indicating that it does not need control.
            if window is None or control is None:
                return func(window, control, *args, **kwargs)
            elif control.element_info.control_type in self.control_types:
                self.wait_visible(window)
                self.wait_visible(control)
                return func(window, control, *args, **kwargs)
            else:
                raise ValueError(f"This function not support control type: {control.element_info.control_type}" +
                                 "Expected control types: [{}]".format(", ".join(self.control_types)))

        # Add the function signature to the wrapper
        wrapper.args = inspect.signature(func)
        # Add function to the operate_dict
        global role_op, op_model_map
        for role in self.roles:
            if role not in role_op:
                role_op[role] = {}
            role_op[role][wrapper.__name__] = wrapper

        op_func_map[wrapper.__name__] = wrapper
        op_model_map[wrapper.__name__] = self.model
        return wrapper
