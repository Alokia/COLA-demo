from typing import Any, Optional, List, Union, Dict, Tuple
import os
from cola.fundamental.base_vectorstore import BaseVectorStore
from pathlib import Path
import numpy as np
import operator
import pickle


def dependable_faiss_import(no_avx2: Optional[bool] = None) -> Any:
    """
    Import faiss if available, otherwise raise error.
    If FAISS_NO_AVX2 environment variable is set, it will be considered
    to load FAISS with no AVX2 optimization.

    Args:
        no_avx2: Load FAISS strictly with no AVX2 optimization
            so that the vectorstore is portable and compatible with other devices.
    """
    if no_avx2 is None and "FAISS_NO_AVX2" in os.environ:
        no_avx2 = bool(os.getenv("FAISS_NO_AVX2"))

    try:
        if no_avx2:
            from faiss import swigfaiss as faiss
        else:
            import faiss
    except ImportError:
        raise ImportError(
            "Could not import faiss python package. "
            "Please install it with `pip install faiss-gpu` (for CUDA supported GPU) "
            "or `pip install faiss-cpu` (depending on Python version)."
        )
    return faiss


class FaissVectorStore(BaseVectorStore):
    def __init__(self, embedding_dim: int,
                 index: Optional[Any] = None,
                 index_to_key: Optional[Dict[int, str]] = None):
        faiss = dependable_faiss_import()
        self.embedding_dim = embedding_dim
        self.index = faiss.IndexFlatIP(embedding_dim) if index is None else index
        self.index_to_key = {} if index_to_key is None else index_to_key

    def __contains__(self, item: str) -> bool:
        return item in self.index_to_key.values()

    def add_embeddings(
            self,
            keys: List[str],
            embeddings: List[List[float]] = None,
            **kwargs: Any,
    ) -> None:
        assert len(keys) == len(
            embeddings
        ), f"keys: {len(keys)}, embeddings: {len(embeddings)} expected to be equal length"

        vector = np.array(embeddings, dtype=np.float32)
        self.index.add(vector)

        starting_len = len(self.index_to_key)
        index_to_key = {starting_len + j: id_ for j, id_ in enumerate(keys)}
        self.index_to_key.update(index_to_key)

    def delete(self, keys: Optional[List[str]] = None, **kwargs: Any) -> Optional[bool]:
        # if keys is None, delete all
        if keys is None:
            keys = list(self.index_to_key.values())

        missing_keys = set(keys).difference(self.index_to_key.values())
        if missing_keys:
            raise ValueError(
                f"Some specified ids do not exist in the current store. Ids not found: "
                f"{missing_keys}"
            )

        reversed_index = {id_: idx for idx, id_ in self.index_to_key.items()}
        index_to_delete = {reversed_index[id_] for id_ in keys}

        self.index.remove_ids(np.fromiter(index_to_delete, dtype=np.int64))
        remaining_ids = [
            id_
            for i, id_ in sorted(self.index_to_key.items())
            if i not in index_to_delete
        ]
        self.index_to_key = {i: id_ for i, id_ in enumerate(remaining_ids)}

        return True

    def similarity_search(
            self, embedding: List[float], k: int = 4, score_threshold: Optional[float] = None, **kwargs: Any
    ) -> List[Tuple[str, float]]:
        if len(self.index_to_key) == 0:
            return []
        vector = np.array([embedding], dtype=np.float32)
        scores, indices = self.index.search(vector, min(k, len(self.index_to_key)))

        key_and_score = [(self.index_to_key[i], score) for i, score in zip(indices[0], scores[0])]

        if score_threshold is not None:
            # TODO: support different distance metrics
            cmp = operator.gt
            key_and_score = [(key, score) for key, score in key_and_score if cmp(score, score_threshold)]
        return key_and_score[:k]

    def save_vectorstore(self, path: Union[str, Path], file_name: str) -> None:
        if isinstance(path, str):
            path = Path(path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        faiss_path = str(path / f"{file_name}.faiss")
        pickle_path = str(path / f"{file_name}.pkl")

        faiss = dependable_faiss_import()
        faiss.write_index(self.index, faiss_path)
        with open(pickle_path, "wb") as f:
            pickle.dump({"embedding_dim": self.embedding_dim, "index_to_key": self.index_to_key}, f)

    @classmethod
    def load_vectorstore(cls, path: Union[str, Path], file_name: str) -> "FaissVectorStore":
        if isinstance(path, str):
            path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Path {path} does not exist.")

        faiss_path = path / f"{file_name}.faiss"
        pickle_path = path / f"{file_name}.pkl"

        if not faiss_path.exists() or not pickle_path.exists():
            raise FileNotFoundError(f"Files {faiss_path} or {pickle_path} do not exist.")

        faiss = dependable_faiss_import()
        index = faiss.read_index(str(faiss_path))
        with open(str(pickle_path), "rb") as f:
            data = pickle.load(f)
            embedding_dim = data["embedding_dim"]
            index_to_key = data["index_to_key"]

        return cls(embedding_dim=embedding_dim, index=index, index_to_key=index_to_key)
