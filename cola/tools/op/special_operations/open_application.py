import pyautogui
from pywinauto.controls.uiawrapper import UIAWrapper
import time
from cola.tools.controller.inspector import WindowsApplicationInspector
from cola.fundamental import BaseEmbedding, BaseVectorStore
from typing import List
from cola.tools.embedding.OpenAIEmbedding import OpenAIEmbedding
from cola.tools.vector_store.FaissVectorStore import FaissVectorStore
from config.config import Config
from functools import partial

config = Config.get_instance()
wai = WindowsApplicationInspector()


class OpenApplicationWithUtools:
    def __init__(self, embedding: BaseEmbedding | None = None,
                 vector_store: BaseVectorStore | None = None):
        self.backend = config["backend"]
        self.embedding = embedding
        self.vector_store = vector_store

        # Shortcut to utools, default is Alt + Space.
        self.utools_shortkey = ["alt", "space"]

    def __get_best_result(self, control_elements: List[UIAWrapper], match: str) -> UIAWrapper | None:
        control_dict = {ele.texts()[0]: ele for ele in control_elements}
        texts = [ele.texts()[0] for ele in control_elements]
        embeddings = [self.embedding.embed_query(text) for text in texts]
        self.vector_store.add_embeddings(texts, embeddings)
        result = self.vector_store.similarity_search(self.embedding.embed_query(match), k=1, score_threshold=0.85)

        self.vector_store.delete()
        if len(result) == 0:
            return None
        return control_dict[result[0][0]]

    def __target_utools(self) -> UIAWrapper:
        time.sleep(1)
        pyautogui.hotkey(*self.utools_shortkey)
        time.sleep(2)

        wai.get_active_application(refresh=True)
        utools_window = wai.target_app_based_root_name("uTools.exe")
        if utools_window is not None:
            return utools_window
        else:
            raise EnvironmentError("Please check utools setting, make sure the callout shortcut is Alt+Space")

    def open_app_with_utools(self, app_name: str) -> UIAWrapper | None:
        wai.get_active_application(refresh=True)

        utools_window = self.__target_utools()
        utools_window.draw_outline()
        # Get all current controls of utools
        wai.get_application_elements(utools_window, refresh=True, control_type_list=[])
        control_ele = wai.app_elements_list[1]  # The input box defaults to the second

        time.sleep(0.5)
        control_ele.draw_outline(colour="red")
        time.sleep(0.5)
        control_ele.click_input(button="left")
        time.sleep(0.5)
        control_ele.type_keys(app_name, pause=0.1, with_spaces=False)  # Enter the app you want to open
        time.sleep(1)

        wai.get_application_elements(utools_window, refresh=True, control_type_list=[])

        control_elements = [
            ele for ele in wai.app_elements_list
            if ele.texts()[0] and ele.texts()[0] not in ["Hi, uTools", "最佳搜索结果", "匹配推荐"]
        ]
        target = self.__get_best_result(control_elements, app_name)
        if target is None:
            return None

        time.sleep(0.5)
        target.draw_outline(colour="red")
        time.sleep(1)
        target.click_input(button="left")
        time.sleep(5)  # Wait for the program to open

        window = wai.target_new_opened_application(refresh=True)
        return window


_embedding = OpenAIEmbedding(
    openai_api_key=config["openai_api_key"],
    openai_api_base=config["openai_api_base"],
    dimensions=100,
)
_vs = FaissVectorStore(embedding_dim=_embedding.get_embedding_dim())

_oa = OpenApplicationWithUtools(
    embedding=_embedding,
    vector_store=_vs
)

op_open_application = partial(_oa.open_app_with_utools)
