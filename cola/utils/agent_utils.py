from typing import Dict
from cola.fundamental.base_role import BaseRole
from functools import wraps

agents_instance: Dict[str, BaseRole] = {}  # When a Role is instantiated it is stored in this dictionary, Role Name: Role Instance
agents_capability: Dict[str, str] = {}  # When a Role is instantiated it is stored in this dictionary, Role Name: Role Capabilities


class RegisterAgent:
    """
    Save all Agent roles and capabilities
    Save all Agent instances
    """

    def __init__(self, ignore_capability: bool = False):
        self.ignore_capability = ignore_capability

    def __call__(self, cls):
        global agents_instance, agents_capability

        @wraps(cls)
        def wrapper(*args, **kwargs):
            instance = cls(*args, **kwargs)
            role = instance.role
            capability = instance.capability

            agents_instance[str(role)] = instance
            if not self.ignore_capability:
                agents_capability[str(role)] = capability
            return instance

        return wrapper
