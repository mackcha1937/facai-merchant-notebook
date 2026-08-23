"""阶段4客户事实候选提取与权威冲突标注。

模型可用时可注入 ModelAdapter 获取严格 JSON；模型不可用时使用保守规则降级。
两条路径都只产生候选，确认前不写 CustomerFact。
"""
import json
import re
import unicodedata

from sqlalchemy.orm import Session

from app.infrastructure.llm.base import ModelError
from app.repositories import customer_facts as fact_repo


ALLOWED_FACT_TYPES = {
    "skin_condition", "skin_sensitivity", "acne_tendency", "adverse_reaction",
    "ingredient_intolerance", "observation", "preference", "contact_preference",
    "marketing_preference", "birthday", "note",
}


def normalize_fact_value(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().lower()
    return re.sub(r"\s+", "", text)


def _candidate(fact_type, value, evidence, confidence, sensitivity="normal") -> dict:
    return {
        "fact_type": fact_type,
        "display_value": value.strip(),
        "normalized_value": normalize_fact_value(value),
        "evidence_text": evidence.strip(),
        "confidence": round(float(confidence), 3),
        "sensitivity_level": sensitivity,
    }


def _rule_candidates(text: str) -> list[dict]:
    candidates: list[dict] = []
    sentences = [part.strip() for part in re.split(r"[。；;\n]", text) if part.strip()]
    for sentence in sentences:
        if re.search(r"不(?:接受|要|喜欢)(?:任何)?(?:营销|推销|促销)|别(?:营销|推销)", sentence):
            candidates.append(_candidate("marketing_preference", "不接受营销", sentence, 0.99))

        adverse = re.search(r"([^，,]{0,24}?)(不适|不舒服|过敏|刺痛|发红|红肿|瘙痒)", sentence)
        if adverse:
            phrase = "".join(adverse.groups()).strip()
            fact_type = "ingredient_intolerance" if re.search(r"香精|成分|含.+的", phrase) else "adverse_reaction"
            candidates.append(_candidate(fact_type, phrase, sentence, 0.92, "sensitive"))

        subjective = re.search(r"(?:看着像|好像|可能是)[^，,]{0,12}(?:敏感|脸红)", sentence)
        if subjective:
            candidates.append(_candidate("observation", subjective.group(0), sentence, 0.68, "sensitive"))

        skin = re.search(r"(?:皮肤|肤质)(?:是|比较|很|有点|偏)?(敏感|干燥|油性|混合)", sentence)
        if skin:
            fact_type = "skin_sensitivity" if skin.group(1) == "敏感" else "skin_condition"
            candidates.append(_candidate(fact_type, skin.group(1), sentence, 0.94, "sensitive"))

        if re.search(r"(?:经常|容易|易)?长痘", sentence):
            candidates.append(_candidate("acne_tendency", "易长痘", sentence, 0.9, "sensitive"))

        contact = re.search(r"((?:不要|别|尽量|可以|适合)[^，,]{0,12}(?:联系|微信|提醒))", sentence)
        if contact:
            candidates.append(_candidate("contact_preference", contact.group(1), sentence, 0.86))

        preference = re.search(r"(?:喜欢|偏好|更喜欢)([^，,]{1,20})", sentence)
        if preference:
            value = re.split(r"(?:，|但是|不过|并且|同时)", preference.group(1))[0].strip()
            if value:
                candidates.append(_candidate("preference", value, sentence, 0.86))

        birthday = re.search(r"生日(?:是|在)?\s*([0-9一二三四五六七八九十]{1,4}月[0-9一二三四五六七八九十]{1,4}[日号]?)", sentence)
        if birthday:
            candidates.append(_candidate("birthday", birthday.group(1), sentence, 0.9, "sensitive"))

    unique = {}
    for item in candidates:
        unique[(item["fact_type"], item["normalized_value"])] = item
    return list(unique.values())


def _model_candidates(text: str, adapter) -> list[dict]:
    prompt = (
        "你只提取店主原话中明确出现的客户事实。输出 JSON 数组，每项仅含 fact_type、"
        "display_value、evidence_text、confidence、sensitivity_level。fact_type 只能是："
        + "、".join(sorted(ALLOWED_FACT_TYPES))
        + "。evidence_text 必须是原文连续片段。健康、不适、生日标 sensitive。不要诊断或推断。"
    )
    raw = adapter.chat(
        [{"role": "system", "content": prompt}, {"role": "user", "content": text}],
        temperature=0.0,
    )
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("事实提取结果不是数组")
    result = []
    for item in data[:10]:
        fact_type = str(item.get("fact_type") or "")
        value = str(item.get("display_value") or "").strip()
        evidence = str(item.get("evidence_text") or "").strip()
        if fact_type not in ALLOWED_FACT_TYPES or not value or not evidence or evidence not in text:
            continue
        confidence = max(0.0, min(1.0, float(item.get("confidence", 0.5))))
        sensitivity = "sensitive" if item.get("sensitivity_level") == "sensitive" else "normal"
        result.append(_candidate(fact_type, value, evidence, confidence, sensitivity))
    return result


def extract_fact_candidates(
    db: Session, customer_id: int, text: str, *, adapter=None
) -> tuple[list[dict], str]:
    source = "rule_fallback"
    items: list[dict]
    if adapter is not None:
        try:
            items = _model_candidates(text, adapter)
            source = "model"
        except (ModelError, ValueError, TypeError, json.JSONDecodeError):
            items = _rule_candidates(text)
    else:
        items = _rule_candidates(text)

    result = []
    for item in items:
        current = fact_repo.get_current_by_type(db, customer_id, item["fact_type"])
        if current and current.normalized_value == item["normalized_value"]:
            continue
        result.append({
            **item,
            "supersedes_id": current.id if current else None,
            "conflict": bool(current),
            "previous_value": current.display_value if current else None,
            "extraction_source": source,
        })
    return result, source
