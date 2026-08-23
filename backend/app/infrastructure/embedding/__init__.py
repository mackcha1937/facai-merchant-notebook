"""阶段5本地 Embedding 与向量存储接口。"""

from .base import EmbeddingAdapter, EmbeddingError, VectorStore
from .local import LocalDeterministicEmbedding, SqliteVectorStore

__all__ = [
    "EmbeddingAdapter", "EmbeddingError", "VectorStore",
    "LocalDeterministicEmbedding", "SqliteVectorStore",
]
