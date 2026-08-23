"""零网络、可版本化的本地确定性 Embedding 与轻量存储。"""
import hashlib
import json
import math
import re

from .base import EmbeddingAdapter, EmbeddingError, EmbeddingVector, VectorStore


class LocalDeterministicEmbedding(EmbeddingAdapter):
    """字符 n-gram 哈希向量；用于 MVP 检索测试，不声称通用语义能力。"""

    provider = "facai-local"
    model = "char-ngram-sha256-v1"
    dimension = 32

    def embed(self, text: str) -> EmbeddingVector:
        normalized = re.sub(r"\s+", "", str(text or "").lower())
        if not normalized:
            raise EmbeddingError("empty_embedding_input")
        vector = [0.0] * self.dimension
        tokens = list(normalized)
        tokens.extend(normalized[index:index + 2] for index in range(max(0, len(normalized) - 1)))
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            slot = int.from_bytes(digest[:4], "big") % self.dimension
            vector[slot] += 1.0 if digest[4] % 2 == 0 else -1.0
        norm = math.sqrt(sum(value * value for value in vector))
        if not norm:
            raise EmbeddingError("zero_embedding_vector")
        values = [round(value / norm, 6) for value in vector]
        return EmbeddingVector(values, self.provider, self.model, self.dimension)


class SqliteVectorStore(VectorStore):
    """MVP 将紧凑向量放入 EmbeddingRecord.vector_ref，不建外部服务。"""

    def put(self, *, document_id: int, chunk_id: int, checksum: str, vector: EmbeddingVector) -> str:
        del document_id, chunk_id, checksum
        payload = json.dumps(vector.values, separators=(",", ":"))
        if len(payload) > 500:
            raise EmbeddingError("vector_ref_too_long")
        return payload

    def load(self, vector_ref: str, *, expected_dimension: int) -> list[float]:
        try:
            values = json.loads(vector_ref)
            if not isinstance(values, list) or len(values) != expected_dimension:
                raise ValueError
            return [float(value) for value in values]
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise EmbeddingError("invalid_vector_ref") from exc
