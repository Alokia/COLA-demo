from cola.memory.json_memory import JsonStringMemory
from cola.tools.vector_store.FaissVectorStore import FaissVectorStore
from cola.tools.embedding.OpenAIEmbedding import OpenAIEmbedding
from config.config import Config
from pathlib import Path
import json
from typing import List, Optional, Dict, Union
from tqdm import tqdm
import re

__all__ = ["load_gaia_examples", "make_gaia_examples"]

config = Config.get_instance()

GAIA_validation_path = Path("GAIA/2023/validation/metadata.jsonl")

openai_embedding = OpenAIEmbedding(config["openai_api_key"], config["openai_api_base"])
faiss_vector_store = FaissVectorStore(openai_embedding.get_embedding_dim())
gaia_memory = JsonStringMemory(openai_embedding, faiss_vector_store)


def data_to_message(data: Dict) -> str:
    steps = ""
    for step in data["steps"][:-1]:
        steps += f"        \"{step}\",\n"
    steps += f"        \"{data['steps'][-1]}\""

    result = "Task:\n{}\n".format(data["task"]) + """Output:
```json
{{
    "sub_tasks": [
{steps}
    ],
    "branch": "Continue",
    "problem": ""
}}
```
""".format(steps=steps)
    return result


def make_gaia_examples(save_path: Union[str, Path], file_name: str,
                       gaia_path: Optional[Union[str, Path]] = None,
                       levels: Optional[List[int]] = None):
    if gaia_path is not None and isinstance(gaia_path, str):
        gaia_path = Path(gaia_path)
        assert gaia_path.exists(), f"File {gaia_path} not found!."
    if gaia_path is None:
        gaia_path = GAIA_validation_path
    if levels is None:
        levels = [1, 2, 3]

    with open(gaia_path, "r", encoding="utf-8") as f:
        f = tqdm(f, desc="Processing GAIA data", total=165)
        for key, line in enumerate(f):
            cur_line = json.loads(line)
            if cur_line["Level"] in levels:
                steps = cur_line["Annotator Metadata"]["Steps"]
                pattern = re.compile(r"\d+\s?\.\s?")
                if steps.startswith("Step"):
                    pattern = re.compile(r"Step\s?\d+\s?:\s?")
                steps = pattern.split(steps)
                steps = [step.strip() for step in steps if step.strip()]

                data = {"task": cur_line["Question"], "steps": steps}
                store = data_to_message(data)
                gaia_memory.add(summary=data["task"], store=store)

    # print(gaia_memory.get_all_memory())
    gaia_memory.save_memory(save_path, file_name)


def load_gaia_examples(path: Union[str, Path], file_name: str):
    gaia_memory.load_memory(path, file_name)
    # print(gaia_memory.get_all_memory())
    return gaia_memory


if __name__ == '__main__':
    make_gaia_examples(*config["gaia_examples_path"])

    # test = "Here's a fun riddle that I'd like you to try.\n\nAn adventurer exploring an ancient tomb came across a horde of gold coins, all neatly stacked in columns. As he reached to scoop them into his backpack, a mysterious voice filled the room. \"You have fallen for my trap adventurer,\" the voice began, and suddenly the doorway to the chamber was sealed by a heavy rolling disk of stone. The adventurer tried to move the stone disk but was unable to budge the heavy stone. Trapped, he was startled when the voice again spoke. \n\n\"If you solve my riddle, I will reward you with a portion of my riches, but if you are not clever, you will never leave this treasure chamber. Before you are 200 gold coins. I pose a challenge to you, adventurer. Within these stacks of coins, all but 30 are face-up. You must divide the coins into two piles, one is yours, and one is mine. You may place as many coins as you like in either pile. You may flip any coins over, but you may not balance any coins on their edges. For every face-down coin in your pile, you will be rewarded with two gold coins. But be warned, if both piles do not contain the same number of face-down coins, the door will remain sealed for all eternity!\"\n\nThe adventurer smiled, as this would be an easy task. All he had to do was flip over every coin so it was face down, and he would win the entire treasure! As he moved to the columns of coins, however, the light suddenly faded, and he was left in total darkness. The adventurer reached forward and picked up one of the coins, and was shocked when he realized that both sides felt almost the same. Without the light, he was unable to determine which side of the coin was heads and which side was tails. He carefully replaced the coin in its original orientation and tried to think of a way to solve the puzzle. Finally, out of desperation, the adventurer removed 30 coins to create his pile. He then carefully flipped over each coin in his pile, so its orientation was inverted from its original state.\n\n\"I've finished,\" he said, and the lights returned. Looking at the two piles, he noticed that the larger pile contained 14 face-down coins.\n\nWhat was the outcome for the adventurer? If he failed the challenge, please respond with \"The adventurer died.\" Otherwise, please provide the number of coins the adventurer won at the conclusion of the riddle. If the adventurer won any coins, provide your response as the number of coins, with no other text."
    #
    # gaia_memory = load_gaia_examples(*gaia_examples_path)
    # print(gaia_memory.similarity_search(test)[0])
