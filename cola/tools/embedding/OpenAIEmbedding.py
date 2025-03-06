from cola.fundamental.base_embedding import BaseEmbedding
from typing import List
from openai import OpenAI
from functools import partial


class OpenAIEmbedding(BaseEmbedding):
    def __init__(self, openai_api_key: str,
                 openai_api_base: str = None,
                 model: str = "text-embedding-3-large",
                 **kwargs):
        assert model in ["text-embedding-ada-002", "text-embedding-3-large", "text-embedding-3-small"], \
            "embedding model must be one of ['text-embedding-ada-002', 'text-embedding-3-large', 'text-embedding-3-small']"
        self.model = model
        self.dimensions = kwargs.get("dimensions", None)
        if self.dimensions is not None:
            assert model in ["text-embedding-3-large", "text-embedding-3-small"], \
                "dimensions can only be specified for text-embedding-3 models"

        self.client = OpenAI(api_key=openai_api_key, base_url=openai_api_base)
        self.embedding = partial(self.client.embeddings.create, model=model, **kwargs)

    def embed_query(self, text: str) -> List[float]:
        text = text.replace("\n", " ")
        return self.embedding(input=[text]).data[0].embedding

    def get_embedding_dim(self) -> int:
        if self.model == "text-embedding-ada-002":
            return 1536
        # If there is a dimension specified, it is returned directly, only valid for embedding-3
        if self.dimensions is not None:
            return self.dimensions
        if self.model == "text-embedding-3-large":
            return 3072
        if self.model == "text-embedding-3-small":
            return 1536
        return len(self.embed_query("test dimensions"))
