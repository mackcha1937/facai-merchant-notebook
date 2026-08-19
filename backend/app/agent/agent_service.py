"""Agent 解析用例：把自然语言转成结构化建议（阶段2不写库）。"""
import json

from app.agent import matching, prompt_loader, schema
from app.agent.whitelist import ensure_allowed_action_types
from app.domain.errors import DomainError
from app.infrastructure.llm.base import ModelError
from app.repositories import customers as customer_repo
from app.repositories import proposals as proposal_repo
from app.repositories import services as service_repo


def build_system_prompt(prompt_content: str, services, customers) -> str:
    service_names = "、".join([s.name for s in services]) or "（无）"
    customer_text = "、".join(
        [
            f"{c.display_name}（别名：{'、'.join(a.alias for a in c.aliases if a.deleted_at is None) or '无'}）"
            for c in customers
        ]
    ) or "（无）"
    example = json.dumps(schema.SCHEMA_EXAMPLE, ensure_ascii=False, indent=2)
    return (
        f"{prompt_content}\n\n"
        f"当前可用的服务项目：{service_names}\n"
        f"当前已有的化名客户：{customer_text}\n\n"
        f"请只输出符合以下 JSON 结构的文本，不要输出 JSON 以外的任何解释：\n{example}"
    )


def interpret(db, text: str, adapter=None) -> dict:
    text = (text or "").strip()
    if not text:
        return {"error": "请输入要解析的内容", "original_input": "", "status": "error"}

    try:
        prompt = prompt_loader.get_active_prompt(db)
    except Exception as exc:  # noqa: BLE001
        return {"error": f"提示词初始化失败：{exc}", "original_input": text, "status": "error"}

    services = [s for s in service_repo.list_services(db) if s.status == "active"]
    customers = customer_repo.list_customers(db)

    if adapter is None:
        from app.infrastructure.llm.deepseek import DeepSeekAdapter

        adapter = DeepSeekAdapter()

    system = build_system_prompt(prompt.content, services, customers)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": text},
    ]

    try:
        raw = adapter.chat(messages, temperature=0.0)
    except ModelError as exc:
        return {"error": str(exc), "original_input": text, "status": "error"}

    try:
        parsed = schema.parse_model_output(raw)
    except schema.AgentParseError as exc:
        return {"error": str(exc), "original_input": text, "status": "error"}

    try:
        ensure_allowed_action_types(parsed.actions)
    except DomainError as exc:
        return {"error": str(exc), "original_input": text, "status": "error"}

    enriched = _enrich(parsed, customers, services)

    proposal_id = None
    try:
        proposal = proposal_repo.create_proposal(
            db,
            original_input=text,
            parsed_json=json.dumps(enriched, ensure_ascii=False),
            prompt_version=prompt.version,
            status="pending",
        )
        db.commit()
        proposal_id = proposal.id
    except Exception:  # noqa: BLE001 - 预览保存失败不应阻断解析结果返回
        db.rollback()
        proposal_id = None

    return {
        "id": proposal_id,
        "status": "pending",
        "write_allowed": False,
        "prompt_version": prompt.version,
        "original_input": text,
        **enriched,
        "error": None,
    }


def _enrich(parsed: schema.AgentOutput, customers, services) -> dict:
    query = (parsed.customer_query or "").strip()

    customer_dicts = [
        {
            "id": c.id,
            "display_name": c.display_name,
            "aliases": [a.alias for a in c.aliases if a.deleted_at is None],
        }
        for c in customers
    ]
    matches = matching.match_customers(query, customer_dicts, limit=3)

    exact = [m for m in matches if m["match_type"] == "exact"]
    if exact:
        cm_status = "exact"
        candidates = exact[:1]
    elif matches:
        cm_status = "fuzzy" if len(matches) == 1 else "ambiguous"
        candidates = matches
    else:
        cm_status = "not_found"
        candidates = []

    customer_match = {
        "status": cm_status,
        "candidate_ids": [m["id"] for m in candidates],
        "candidates": candidates,
        "new_customer_name": query if cm_status == "not_found" and query else None,
    }

    service_dicts = [{"id": s.id, "name": s.name} for s in services]
    actions = []
    for action in parsed.actions:
        item = {
            "type": action.type,
            "service_name": action.service_name,
            "product_name": action.product_name,
            "quantity": action.quantity,
            "price": action.price,
            "price_cents": _price_to_cents(action.price),
            "total_count": action.total_count,
            "purchased_on": action.purchased_on,
            "service_match": None,
        }
        if action.service_name:
            item["service_match"] = _match_service(action.service_name, service_dicts)
        actions.append(item)

    return {
        "customer_query": query or parsed.customer_query,
        "customer_match": customer_match,
        "actions": actions,
        "needs_clarification": parsed.needs_clarification,
        "clarification_question": parsed.clarification_question,
    }


def _match_service(name: str, service_dicts: list[dict]) -> dict | None:
    matches = matching.match_services(name, service_dicts, limit=3)
    if not matches:
        return {"status": "not_found", "resolved_service_id": None, "candidates": []}
    if matches[0]["match_type"] == "exact":
        return {"status": "exact", "resolved_service_id": matches[0]["id"], "candidates": matches}
    if len(matches) == 1:
        return {"status": "fuzzy", "resolved_service_id": matches[0]["id"], "candidates": matches}
    return {"status": "ambiguous", "resolved_service_id": None, "candidates": matches}


def _price_to_cents(price) -> int | None:
    if price is None:
        return None
    try:
        value = float(price)
    except (TypeError, ValueError):
        return None
    if value < 0:
        return None
    return int(round(value * 100))
