"""阶段4产品实体解析：canonical/alias/fuzzy/本地语义候选，不接 RAG。"""
import hashlib
import math
import re
import unicodedata
from difflib import SequenceMatcher

from sqlalchemy.orm import Session

from app.repositories import products as product_repo


_UNITS = "瓶|盒|支|件|套|袋|罐"
_CHINESE_NUMBERS = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def _quantity(value: str) -> int:
    return int(value) if value.isdigit() else _CHINESE_NUMBERS.get(value, 1)


def extract_product_purchase(text: str) -> dict | None:
    """保守识别明确购买表达；不把普通提及误写成购买。"""
    match = re.search(r"(?:买了|购买了?|带走了?|拿了|要了)\s*([^，。；;]+)", text)
    if not match:
        return None
    phrase = match.group(1).strip()
    before = re.match(rf"^([一二三四五六七八九十两\d]+)\s*(?:{_UNITS})?\s*(.+)$", phrase)
    quantity = 1
    if before:
        quantity = _quantity(before.group(1))
        phrase = before.group(2).strip()
    after = re.search(rf"(.+?)\s*([一二三四五六七八九十两\d]+)\s*(?:{_UNITS})\s*$", phrase)
    if after:
        phrase = after.group(1).strip()
        quantity = _quantity(after.group(2))
    phrase = re.sub(r"^(?:今天|昨天|前天|明天)\s*", "", phrase).strip()
    if not phrase or quantity < 1:
        return None
    return {"query": phrase, "quantity": quantity}


def normalize_product_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower().strip()
    return re.sub(r"[\s\-—_·,，。./\\（）()]+", "", text)


def _ngrams(value: str) -> list[str]:
    if not value:
        return []
    padded = f"^{value}$"
    return [padded[i : i + 2] for i in range(max(1, len(padded) - 1))]


def _hash_embedding(value: str, dimension: int = 96) -> list[float]:
    """稳定的本地字符 n-gram 向量，仅用于产品名候选，不写向量库。"""
    vector = [0.0] * dimension
    for token in _ngrams(value):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        vector[index] += -1.0 if digest[4] & 1 else 1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _product_payload(product, aliases, *, score: float = 1.0, method: str = "canonical") -> dict:
    return {
        "id": product.id,
        "name": product.canonical_name,
        "canonical_name": product.canonical_name,
        "brand": product.brand,
        "category": product.category,
        "spec": product.specification,
        "specification": product.specification,
        "aliases": [a.alias for a in aliases],
        "lifecycle_status": product.lifecycle_status,
        "knowledge_status": product.knowledge_status,
        "score": round(max(0.0, min(1.0, score)), 4),
        "match_method": method,
    }


def resolve_product(
    db: Session,
    query: str,
    *,
    brand: str | None = None,
    specification: str | None = None,
    limit: int = 3,
) -> dict:
    safe_limit = min(max(limit, 1), 3)
    normalized_query = normalize_product_text(query)
    recognized = {
        "name": str(query or "").strip() or None,
        "brand": str(brand).strip() if brand else None,
        "specification": str(specification).strip() if specification else None,
    }
    missing_fields = [key for key in ("brand", "specification") if not recognized[key]]
    if len(normalized_query) < 2:
        return {
            "status": "insufficient", "query": query, "recognized": recognized,
            "missing_fields": ["name", *missing_fields], "candidates": [],
            "embedding_mode": "local_name_hash", "rag_used": False,
        }

    products = product_repo.list_products(db)
    alias_rows = product_repo.list_aliases(db, [p.id for p in products])
    aliases_by_product: dict[int, list] = {}
    for alias in alias_rows:
        aliases_by_product.setdefault(alias.product_id, []).append(alias)

    exact = []
    scored = []
    query_vector = _hash_embedding(normalized_query)
    normalized_brand = normalize_product_text(brand)
    normalized_spec = normalize_product_text(specification)
    for product in products:
        aliases = aliases_by_product.get(product.id, [])
        canonical = normalize_product_text(product.canonical_name)
        full = normalize_product_text(
            "".join(filter(None, (product.brand, product.canonical_name, product.specification)))
        )
        names = [(canonical, "canonical"), (full, "canonical")]
        names.extend(
            (normalize_product_text(alias.normalized_alias or alias.alias), "alias") for alias in aliases
        )
        matched_methods = {method for value, method in names if value == normalized_query}
        brand_ok = not normalized_brand or normalize_product_text(product.brand) == normalized_brand
        spec_ok = not normalized_spec or normalize_product_text(product.specification) == normalized_spec
        if matched_methods and brand_ok and spec_ok:
            method = "canonical" if "canonical" in matched_methods else "alias"
            exact.append(_product_payload(product, aliases, method=method))
            continue

        string_score = max(
            SequenceMatcher(None, normalized_query, value).ratio() for value, _ in names if value
        )
        embedding_score = max(
            _cosine(query_vector, _hash_embedding(value)) for value, _ in names if value
        )
        if normalized_brand and normalize_product_text(product.brand) == normalized_brand:
            string_score = min(1.0, string_score + 0.08)
            embedding_score = min(1.0, embedding_score + 0.05)
        if normalized_spec and normalize_product_text(product.specification) == normalized_spec:
            string_score = min(1.0, string_score + 0.08)
            embedding_score = min(1.0, embedding_score + 0.05)
        method = "fuzzy" if string_score >= embedding_score else "embedding"
        score = max(string_score, embedding_score)
        scored.append(_product_payload(product, aliases, score=score, method=method))

    if exact:
        candidates = exact[:safe_limit]
        return {
            "status": "exact" if len(exact) == 1 else "ambiguous",
            "query": query, "recognized": recognized, "missing_fields": missing_fields,
            "matched": candidates[0] if len(exact) == 1 else None,
            "candidates": candidates, "embedding_mode": "local_name_hash", "rag_used": False,
        }

    scored.sort(key=lambda item: (-item["score"], item["id"]))
    candidates = [item for item in scored if item["score"] >= 0.48][:safe_limit]
    if not candidates:
        return {
            "status": "not_found", "query": query, "recognized": recognized,
            "missing_fields": missing_fields, "candidates": [],
            "embedding_mode": "local_name_hash", "rag_used": False,
        }
    top = candidates[0]
    second_score = candidates[1]["score"] if len(candidates) > 1 else 0.0
    decisive = top["score"] >= 0.72 and top["score"] - second_score >= 0.08
    return {
        "status": "fuzzy" if decisive else "ambiguous",
        "query": query, "recognized": recognized, "missing_fields": missing_fields,
        "matched": top if decisive else None, "candidates": candidates,
        "embedding_mode": "local_name_hash", "rag_used": False,
    }
