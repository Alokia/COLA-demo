from cola.Interactor import Interactor
from cola.Planner import Planner
from cola.TaskScheduler import TaskScheduler
from cola.Executor import Executor
from cola.Reviewer import Reviewer

from cola.role.Searcher import Searcher
from cola.role.ApplicationManager import ApplicationManager
from cola.role.Programmer import Programmer
from cola.role.FileManager import FileManager

from cola.workflow import Workflow
from cola.memory.json_memory import JsonChatMessageMemory
from cola.memory.queue_memory import QueueMemory
from cola.tools.vector_store.FaissVectorStore import FaissVectorStore
from cola.tools.embedding.OpenAIEmbedding import OpenAIEmbedding
from cola.tools.summary.OpenAISummarization import OpenAISummarization
from cola.utils.agent_utils import agents_instance, agents_capability
from cola.utils.print_utils import format_print_dict
from cola.utils.datatype import RoleType, WorkflowEvent
from cola.utils.data_utils import ContextualDataCenter, PrivateData

from LMs import create_lm_model
from config.config import Config
from typing import Dict, Optional

config = Config.get_instance()
cdc = ContextualDataCenter()
openai_api_key = config["openai_api_key"]
openai_api_base = config["openai_api_base"]
root_path = config["root_path"]

roles = [Searcher, ApplicationManager, Programmer, FileManager]
base_roles = [Planner, TaskScheduler, Executor, Reviewer, Interactor]


def init_role(role, role_config: Optional[Dict]):
    if not role_config:
        if role.role == RoleType.Interactor:
            role(agents_instance=agents_instance, agents_capability=agents_capability)
        else:
            role(agents_capability=agents_capability)
        return

    lm = None
    if "lm_name" in role_config and "lm_params" in role_config:
        lm = create_lm_model(role_config["lm_name"], **role_config["lm_params"])

    embedding = None
    if "embedding_model" in role_config and "embedding_model_params" in role_config:
        embedding = OpenAIEmbedding(**role_config["embedding_model_params"])

    summarizer = None
    if "summarizer_model" in role_config and role_config["enable_summarizer"] and (
            "summarizer_model_params" in role_config):
        summarizer = OpenAISummarization(**role_config["summarizer_model_params"])

    ltms = None
    if embedding is not None:
        ltms = JsonChatMessageMemory(
            embedding=embedding,
            vectorstore=FaissVectorStore(embedding_dim=embedding.get_embedding_dim()),
            summarizer=summarizer
        )
        if role_config["load_cache"]:
            ltms.load_memory(path=root_path / role_config["cache_folder"], file_name=role_config["cache_name"])

    interact_mode = config["interact_mode"] if (
            "interact_mode" not in role_config or not role_config["interact_mode"]
    ) else role_config["interact_mode"]

    role(
        lm=lm, agents_capability=agents_capability,
        long_term_memory_store=ltms, short_term_memory_store=QueueMemory(),
        n_chat_message_history=role_config["n_chat_message_history"],
        n_short_message_history=role_config["n_short_message_history"],
        interact_mode=interact_mode
    )


if __name__ == '__main__':
    for role in (roles + base_roles):
        if role.role not in config["agent"]:
            raise ValueError(f"role: {role.role} not in config.agent")
        role_config = config["agent"][role.role]
        init_role(role, role_config)

    workflow = Workflow(agents_instance)

    with open("task.txt", "r") as f:
        task = f.read()

    data = PrivateData(
        sender=RoleType.Human,
        receiver=RoleType.Interactor,
        event=WorkflowEvent.Interactor_start_task,
        task=task
    )
    data = workflow.step(data)
    if isinstance(data, str):
        print("answer:", data)

    for role, instance in agents_instance.items():
        if role != RoleType.Interactor and role != RoleType.Executor:
            if input("save memory for role: {}? (y/n)".format(role)) == "y":
                instance.handle_store_memory(
                    session_id=config["session_id"],
                    mode="cw",
                )
                instance.lt_memory_store.save_memory(
                    path=root_path / config["agent"][role]["cache_folder"],
                    file_name=config["agent"][role]["cache_name"]
                )
                print("memory saved for role: {}".format(role))
