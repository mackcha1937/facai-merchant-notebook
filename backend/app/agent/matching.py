"""客户与服务模糊匹配（由后端权威计算，不信任模型给出的 ID）。

匹配策略：
- exact：完全相同
- contains：互相包含（子串）
- fuzzy：字符串相似度（difflib），达到阈值才算候选
"""
import difflib

_FUZZY_THRESHOLD = 0.6
_TYPE_RANK = {"exact": 2, "contains": 1, "fuzzy": 0}


def _score(query: str, name: str) -> tuple[float, str]:
    if query == name:
        return 1.0, "exact"
    if query in name or name in query:
        ratio = difflib.SequenceMatcher(None, query, name).ratio()
        return max(0.6, ratio), "contains"
    ratio = difflib.SequenceMatcher(None, query, name).ratio()
    return ratio, "fuzzy"


def match_customers(query: str, customers: list[dict], limit: int = 3) -> list[dict]:
    """customers: [{id, display_name, aliases: [str]}]"""
    q = (query or "").strip()
    if not q:
        return []
    results: list[dict] = []
    for c in customers:
        names = [str(c.get("display_name") or "")] + [str(a) for a in (c.get("aliases") or [])]
        best_score = 0.0
        best_type = "fuzzy"
        for name in names:
            if not name:
                continue
            score, mtype = _score(q, name)
            if score > best_score:
                best_score = score
                best_type = mtype
        if best_type in ("exact", "contains") or best_score >= _FUZZY_THRESHOLD:
            results.append(
                {
                    "id": c.get("id"),
                    "display_name": c.get("display_name"),
                    "aliases": c.get("aliases") or [],
                    "score": round(best_score, 3),
                    "match_type": best_type,
                }
            )
    results.sort(key=lambda x: (_TYPE_RANK[x["match_type"]], x["score"]), reverse=True)
    return results[:limit]


def match_services(query: str, services: list[dict], limit: int = 3) -> list[dict]:
    """services: [{id, name}]"""
    q = (query or "").strip()
    if not q:
        return []
    results: list[dict] = []
    for s in services:
        name = str(s.get("name") or "")
        if not name:
            continue
        score, mtype = _score(q, name)
        if mtype in ("exact", "contains") or score >= _FUZZY_THRESHOLD:
            results.append(
                {
                    "id": s.get("id"),
                    "name": name,
                    "score": round(score, 3),
                    "match_type": mtype,
                }
            )
    results.sort(key=lambda x: (_TYPE_RANK[x["match_type"]], x["score"]), reverse=True)
    return results[:limit]
