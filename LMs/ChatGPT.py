from cola.fundamental.base_lm import BaseLM
from openai import OpenAI
from PIL import Image
from cola.utils.image_utils import encode_pil_image_to_base64
from functools import partial
from typing import List, Dict


class ChatGPT(BaseLM):
    def __init__(self, openai_api_key: str, openai_api_base: str,
                 model: str = "gpt-4o-2024-08-06", **kwargs):
        self.client = OpenAI(api_key=openai_api_key, base_url=openai_api_base)

        self.format_chat = partial(
            self.client.beta.chat.completions.parse, model=model, **kwargs)
        self.normal_chat = partial(
            self.client.chat.completions.create, model=model, **kwargs)

    @staticmethod
    def create_message(text: str, image: Image.Image = None, role: str = "user"):
        if image is None:
            content = text
        else:
            img_base64 = encode_pil_image_to_base64(image)
            content = [
                {"type": "text", "text": text},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"},
                },
            ]
        message = {"role": role, "content": content}
        return message

    def query(self, messages: List[Dict[str, str]], response_format=None, **kwargs):
        if response_format is None:
            completion = self.normal_chat(messages=messages, **kwargs)
            return completion.choices[0].message.content
        else:
            completion = self.format_chat(messages=messages, response_format=response_format, **kwargs)
            msg = completion.choices[0].message
            if msg.refusal:
                raise ValueError(f"OpenAI refused the request: {msg.refusal}")
            return msg.parsed
