from cola.fundamental.singleton import Singleton
from pathlib import Path
from typing import Union, Any, Dict, Optional, Tuple, List
from cola.utils.json_utils import save_json, load_json
from cola.utils.datatype import RoleType, RoleKey


class ContextualDataCenter(metaclass=Singleton):
    switch_to: RoleType = None  # handoff flag params

    def __init__(self):
        # Storing input data for each agent for fallbacks
        self._session_data: Dict[RoleType, PrivateData] = PrivateData()  # <role space>, role: context_data
        # Store per-agent query parameters for fallbacks
        self._query_params: Dict[RoleType, Tuple[List, Dict]] = PrivateData()  # <role space>, role: query_params
        # Storing Role's public data
        self.role_context: PrivateData = PrivateData(**{str(k): None for k in RoleKey})
        self.role_context.role_infos = []
        # Storing public data for sessions
        self.session_context: PrivateData = PrivateData()
        # Storing Private Data for Base Role
        self.base_role_context: PrivateData = PrivateData()
        # Storing data for Summary
        self.summary_context: PrivateData = PrivateData(**{str(k): PrivateData() for k in RoleType})

    def set_context(self, role: RoleType, data: 'PrivateData') -> None:
        self._session_data[role] = data

    def set_query_params(self, role: RoleType, params: Tuple[List, Dict]) -> None:
        self._query_params[role] = params

    def get_context(self, role: RoleType) -> 'PrivateData':
        return self._session_data[role]

    def get_query_params(self, role: RoleType) -> Tuple[List, Dict]:
        return self._query_params[role]

    def create_base_role_context_space(self, role: RoleType) -> None:
        self.base_role_context[role] = PrivateData()

    def prepare_data(self, role: RoleType, data: 'PrivateData') -> 'PrivateData':
        # data need contains session_context
        return_data = PrivateData(**self.session_context)
        if role in [RoleType.Planner, RoleType.Interactor, RoleType.TaskScheduler,
                    RoleType.Executor, RoleType.Reviewer]:
            if role in self.base_role_context:
                # If a base role, data need contains base_role_context
                return_data.update(self.base_role_context[role])
        else:
            # If a role, data need contains role_context
            return_data.update(self.role_context)
        # last merge top level data
        return_data.update(data)
        return return_data


class PrivateData(dict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")

    def __setattr__(self, key, value):
        self[key] = value

    def to_dict(self) -> Dict:
        return dict(**self)

    def save_data(self, path: Union[str, Path], file_name: str):
        save_json(Path(path) / (file_name + ".json"), self)

    def load_data(self, path: Union[str, Path], file_name: str):
        self.clear()
        data = load_json(Path(path) / (file_name + ".json"))
        self.update(data)


class SharedData(PrivateData, metaclass=Singleton):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
