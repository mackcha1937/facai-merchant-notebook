"""阶段4客户事实候选提取与权威冲突标注。

模型候选必须先经 stage4_model_service 的严格校验；本模块再与
保守规则去重合并并标注权威冲突。两条路径都只产生候选，
确认前不写 CustomerFact。
"""
import re
import unicodedata

from sqlalchemy.orm import Session

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


def extract_fact_candidates(
    db: Session,
    customer_id: int,
    text: str,
    *,
    validated_model_items: list[dict] | None = None,
) -> tuple[list[dict], str]:
    rules = _rule_candidates(text)
    model_items = [
        _candidate(
            item["fact_type"], item["display_value"], item["evidence_text"],
            item["confidence"], item["sensitivity_level"],
        )
        for item in (validated_model_items or [])
        if item.get("fact_type") in ALLOWED_FACT_TYPES
    ]
    source = "model_and_rules" if model_items else "rule_fallback"
    unique = {
        (item["fact_type"], item["normalized_value"]): {**item, "extraction_source": "model"}
        for item in model_items
    }
    for item in rules:
        unique.setdefault(
            (item["fact_type"], item["normalized_value"]),
            {**item, "extraction_source": "rule"},
        )

    result = []
    for item in unique.values():
        current = fact_repo.get_current_by_type(db, customer_id, item["fact_type"])
        if current and current.normalized_value == item["normalized_value"]:
            continue
        result.append({
            **item,
            "supersedes_id": current.id if current else None,
            "conflict": bool(current),
            "previous_value": current.display_value if current else None,
            "extraction_source": item["extraction_source"],
        })
    return result, source
