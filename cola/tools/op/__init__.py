from .ops import *
from .op_utils import role_op, role_op_model, op_model_map, op_func_map, verify_op_params, get_ops_description, get_ops_function_dict
from typing import Union, Type
from pydantic import BaseModel, Field, model_validator, field_validator, create_model


def OpType(role: RoleType) -> Type[BaseModel]:
    def _verify_function(cls, v):
        if v not in role_op[role]:
            raise ValueError(f"`function` must be one of {list(role_op[role].keys())}, but got {v}")
        return v

    def _check_func_and_params_match(self):
        expected_model = op_model_map[self.function]
        try:
            params = expected_model(**self.params.dict())
            return self
        except Exception as e:
            raise ValueError(e)

    _validators = {
        "verify_function": field_validator("function")(_verify_function),
        "check_func_and_params_match": model_validator(mode='after')(_check_func_and_params_match)
    }

    function_desc = "The function to be executed, can be: {}.".format(", ".join(list(role_op[role].keys())))
    params_desc = "The parameters of the function to be executed."
    params_type = Union[*role_op_model[role]] if len(role_op_model[role]) > 1 else Optional[role_op_model[role][0]]
    model = create_model(
        "OpType",
        function=(str, Field(..., description=function_desc)),
        params=(params_type, Field(..., description=params_desc)),
        __validators__=_validators
    )
    return model
