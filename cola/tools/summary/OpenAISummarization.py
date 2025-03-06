from typing import List, Dict
from cola.fundamental.base_summarization import BaseSummarization
from LMs.ChatGPT import ChatGPT


class OpenAISummarization(BaseSummarization):
    def __init__(self, openai_api_key: str,
                 openai_api_base: str = None,
                 model: str = "gpt-4o",
                 **kwargs):
        self.chat_model = ChatGPT(
            openai_api_key=openai_api_key,
            openai_api_base=openai_api_base,
            model=model,
            **kwargs
        )

        self.summarize_message = [{"role": "user", "content": """According to the conversation, write a concise summary for the conversation.
Don't include unnecessary information. Just write the main points.
CONCISE SUMMARY:"""}]

    def summarize(self, messages: List[Dict]) -> str:
        res = self.chat_model.query(messages + self.summarize_message)
        return res
