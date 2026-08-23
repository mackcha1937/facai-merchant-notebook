"""与供应商无关的 Embedding 和 VectorStore 契约。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


class EmbeddingError(RuntimeError):
    """本地编码或索引失败；上层必须安全降级。"""


@dataclass(frozen=True)
class EmbeddingVector:
    values: list[float]
    provider: str
    model: str
    dimension: int


class EmbeddingAdapter(ABC):
    provider: str
    model: str
    dimension: int

    @abstractmethod
    def embed(self, text: str) -> EmbeddingVector:
        raise NotImplementedError


class VectorStore(ABC):
    @abstractmethod
    def put(self, *, document_id: int, chunk_id: int, checksum: str, vector: EmbeddingVector) -> str:
        raise NotImplementedError

    @abstractmethod
    def load(self, vector_ref: str, *, expected_dimension: int) -> list[float]:
        raise NotImplementedError
