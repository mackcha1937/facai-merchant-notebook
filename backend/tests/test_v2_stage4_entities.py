"""阶段4客户事实与产品实体闭环测试；不涉及 RAG。"""
import json
from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select

from app.application import (
    conversation_service, product_resolution_service, stage3_proposal_service,
    stage4_entity_service,
)
from app.core.tenant import set_current_owner_id, set_current_tenant_id
from app.domain.errors import ConflictError, DomainError, NotFoundError
from app.infrastructure.models import AgentProposal, CustomerFact, LedgerEntry, Product
from app.repositories import customers as customer_repo
from app.repositories import products as product_repo
from app.schemas.conversation import (
    ChatTurnRequest, ProductDraftProposalRequest, ProductMergeProposalRequest,
    ProductResolutionChoiceRequest, ProposalConfirmRequest,
    ProposalCancelRequest,
)


NOW = datetime(2026, 8, 23, 4, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def tenant_context():
    set_current_tenant_id(1)
    set_current_owner_id(1)
    yield
    set_current_tenant_id(None)
    set_current_owner_id(None)


def seed_customer(db):
    customer = customer_repo.create_customer(db, "测试顾客甲", ["甲姐"])
    db.commit()
    return customer


def add_product(db, name, aliases=(), **fields):
    product = product_repo.create_product(db, canonical_name=name, **fields)
    for alias in aliases:
        product_repo.add_alias(
            db, product, alias, product_resolution_service.normalize_product_text(alias), source="test"
        )
    db.commit()
    return product


def chat(db, text, key):
    return conversation_service.chat_turn(
        db,
        ChatTurnRequest(
            text=text, request_id=f"request-{key}", idempotency_key=f"turn-{key}", device_id="phone"
        ),
        now=NOW,
    )


def confirm(db, proposal, key):
    return stage3_proposal_service.confirm(
        db, proposal["id"],
        ProposalConfirmRequest(
            idempotency_key=f"confirm-{key}", device_id="phone",
            data_version=proposal["data_version"],
        ),
        now=NOW,
    )


def test_product_resolution_exact_alias_fuzzy_and_limit(db_session):
    exact = add_product(db_session, "净痘修护面霜", aliases=("痘痘霜",), brand="发财", specification="50ml")
    for index in range(4):
        add_product(db_session, f"净痘修护面膜{index}")

    canonical = product_resolution_service.resolve_product(db_session, "净痘修护面霜")
    alias = product_resolution_service.resolve_product(db_session, "痘痘霜")
    fuzzy = product_resolution_service.resolve_product(db_session, "净痘修护面霜霜")
    assert canonical["status"] == "exact" and canonical["matched"]["id"] == exact.id
    assert alias["status"] == "exact" and alias["matched"]["match_method"] == "alias"
    assert fuzzy["status"] in {"fuzzy", "ambiguous"}
    assert len(fuzzy["candidates"]) <= 3
    assert fuzzy["rag_used"] is False
    assert fuzzy["embedding_mode"] == "local_name_hash"


def test_fact_candidates_are_not_written_before_confirmation(db_session):
    customer = seed_customer(db_session)
    result = chat(db_session, "甲姐皮肤敏感，而且不接受营销。", "facts")
    proposal = result["proposal"]
    fact_actions = [a for a in proposal["actions"] if a["type"] == "upsert_customer_fact"]
    assert len(fact_actions) == 2
    assert any(a["sensitivity_level"] == "sensitive" for a in fact_actions)
    assert all(a["evidence_text"] for a in fact_actions)
    assert db_session.scalar(select(func.count(CustomerFact.id))) == 0

    confirmed = confirm(db_session, proposal, "facts")
    assert confirmed["status"] == "confirmed"
    facts = db_session.scalars(select(CustomerFact).where(CustomerFact.customer_id == customer.id)).all()
    assert len(facts) == 2
    assert all(f.confirmation_status == "confirmed" for f in facts)


def test_conflicting_fact_creates_new_version_and_closes_old(db_session):
    customer = seed_customer(db_session)
    first = chat(db_session, "甲姐肤质干燥。", "fact-v1")["proposal"]
    confirm(db_session, first, "fact-v1")
    old = db_session.scalar(select(CustomerFact).where(CustomerFact.customer_id == customer.id))

    second = chat(db_session, "甲姐肤质油性。", "fact-v2")["proposal"]
    action = next(a for a in second["actions"] if a["type"] == "upsert_customer_fact")
    assert action["conflict"] is True
    assert action["supersedes_id"] == old.id
    confirm(db_session, second, "fact-v2")
    db_session.refresh(old)
    current = db_session.scalar(
        select(CustomerFact).where(CustomerFact.customer_id == customer.id, CustomerFact.valid_to.is_(None))
    )
    assert old.valid_to is not None
    assert current.display_value == "油性"
    assert current.supersedes_id == old.id


def test_new_product_purchase_and_fact_share_one_atomic_proposal(db_session):
    customer = seed_customer(db_session)
    resolving = chat(
        db_session, "甲姐皮肤敏感，今天买了星云修护霜2瓶。", "new-product"
    )
    assert resolving["status"] == "resolving"
    assert resolving["proposal"]["product_match"]["status"] == "not_found"
    assert db_session.scalar(select(func.count(Product.id))) == 0

    pending = stage4_entity_service.resolve_proposal_product(
        db_session, resolving["proposal"]["id"],
        ProductResolutionChoiceRequest(
            data_version=1, idempotency_key="resolve-new-product",
            create_new=True, canonical_name="星云修护霜", brand="测试品牌", specification="50ml",
        ),
    )["proposal"]
    assert len(pending["actions"]) == 2
    assert db_session.scalar(select(func.count(Product.id))) == 0

    result = confirm(db_session, pending, "new-product")
    assert len(result["results"]) == 2
    product = db_session.scalar(select(Product))
    ledger = db_session.scalar(select(LedgerEntry))
    fact = db_session.scalar(select(CustomerFact))
    assert product.lifecycle_status == "draft"
    assert product.knowledge_status == "incomplete"
    assert ledger.product_id == product.id and ledger.customer_id == customer.id
    assert ledger.quantity == 2
    assert fact.customer_id == customer.id


def test_fuzzy_product_requires_owner_choice_before_final_confirmation(db_session):
    seed_customer(db_session)
    product = add_product(db_session, "舒缓修护面膜")
    resolving = chat(db_session, "甲姐今天买了舒缓修复面膜1盒。", "fuzzy-choice")
    assert resolving["status"] == "resolving"
    with pytest.raises(ConflictError) as error:
        confirm(db_session, resolving["proposal"], "too-early")
    assert error.value.payload["conflict_type"] == "product_resolution_required"

    pending = stage4_entity_service.resolve_proposal_product(
        db_session, resolving["proposal"]["id"],
        ProductResolutionChoiceRequest(
            data_version=1, idempotency_key="resolve-existing-product", product_id=product.id
        ),
    )["proposal"]
    confirm(db_session, pending, "fuzzy-choice")
    assert db_session.scalar(select(LedgerEntry.product_id)) == product.id


def test_manual_product_create_and_merge_both_use_proposals(db_session):
    first = stage4_entity_service.create_product_proposal(
        db_session,
        ProductDraftProposalRequest(
            canonical_name="水润精华", aliases=["补水精华"],
            request_id="request-product-first", idempotency_key="proposal-product-first",
        ),
    )["proposal"]
    confirm(db_session, first, "product-first")
    second = stage4_entity_service.create_product_proposal(
        db_session,
        ProductDraftProposalRequest(
            canonical_name="水润精华液", request_id="request-product-second",
            idempotency_key="proposal-product-second",
        ),
    )["proposal"]
    confirm(db_session, second, "product-second")
    products = db_session.scalars(select(Product).order_by(Product.id)).all()

    merge = stage4_entity_service.create_merge_proposal(
        db_session,
        ProductMergeProposalRequest(
            source_product_id=products[1].id, target_product_id=products[0].id,
            request_id="request-product-merge", idempotency_key="proposal-product-merge",
        ),
    )["proposal"]
    confirm(db_session, merge, "product-merge")
    db_session.refresh(products[1])
    assert products[1].lifecycle_status == "replaced"
    assert products[1].merged_into_id == products[0].id


def test_stage4_tenant_isolation_for_product_and_fact(db_session):
    customer = seed_customer(db_session)
    product = add_product(db_session, "租户一面霜")
    proposal = chat(db_session, "甲姐皮肤敏感。", "tenant-fact")["proposal"]
    set_current_tenant_id(2)
    set_current_owner_id(2)
    assert product_resolution_service.resolve_product(db_session, "租户一面霜")["status"] == "not_found"
    with pytest.raises(NotFoundError):
        stage3_proposal_service.confirm(
            db_session, proposal["id"],
            ProposalConfirmRequest(
                idempotency_key="confirm-cross-tenant-stage4", data_version=1, device_id="web"
            ),
            now=NOW,
        )
    assert product.id and customer.id


def test_atomic_rollback_does_not_leave_new_product_or_fact(db_session):
    seed_customer(db_session)
    resolving = chat(db_session, "甲姐皮肤敏感，今天买了回滚霜1瓶。", "rollback-product")
    pending = stage4_entity_service.resolve_proposal_product(
        db_session, resolving["proposal"]["id"],
        ProductResolutionChoiceRequest(
            data_version=1, idempotency_key="resolve-rollback-product",
            create_new=True, canonical_name="回滚霜",
        ),
    )["proposal"]
    row = db_session.get(AgentProposal, pending["id"])
    parsed = json.loads(row.parsed_json)
    parsed["actions"][0]["fact_type"] = "forbidden_type"
    row.parsed_json = json.dumps(parsed, ensure_ascii=False)
    db_session.commit()
    with pytest.raises(DomainError):
        confirm(db_session, pending, "rollback-product")
    assert db_session.scalar(select(func.count(Product.id))) == 0
    assert db_session.scalar(select(func.count(LedgerEntry.id))) == 0
    assert db_session.scalar(select(func.count(CustomerFact.id))) == 0


def test_voice_transcript_can_remove_sensitive_fact_and_confirm_remaining(db_session):
    seed_customer(db_session)
    proposal = chat(db_session, "甲姐皮肤敏感，而且不接受营销。", "voice-facts")["proposal"]
    edited = conversation_service.chat_turn(
        db_session,
        ChatTurnRequest(
            text="去掉敏感肤质", request_id="request-voice-remove-fact",
            idempotency_key="voice-remove-fact-key", device_id="phone",
        ),
        now=NOW,
    )["proposal"]
    assert len(edited["actions"]) == 1
    assert edited["actions"][0]["fact_type"] == "marketing_preference"
    result = conversation_service.chat_turn(
        db_session,
        ChatTurnRequest(
            text="确认", request_id="request-voice-confirm-fact",
            idempotency_key="voice-confirm-fact-key", device_id="phone",
        ),
        now=NOW,
    )
    assert result["status"] == "confirmed"
    facts = db_session.scalars(select(CustomerFact)).all()
    assert [fact.fact_type for fact in facts] == ["marketing_preference"]
    assert proposal["id"] == edited["id"]


def test_voice_transcript_can_resolve_new_product_then_confirm(db_session):
    seed_customer(db_session)
    resolving = chat(db_session, "甲姐今天买了语音新品霜1瓶。", "voice-product")
    assert resolving["status"] == "resolving"
    pending = conversation_service.chat_turn(
        db_session,
        ChatTurnRequest(
            text="作为新产品", request_id="request-voice-new-product",
            idempotency_key="voice-new-product-key", device_id="phone",
        ),
        now=NOW,
    )
    assert pending["status"] == "pending"
    confirmed = conversation_service.chat_turn(
        db_session,
        ChatTurnRequest(
            text="确认", request_id="request-voice-confirm-product",
            idempotency_key="voice-confirm-product-key", device_id="phone",
        ),
        now=NOW,
    )
    assert confirmed["status"] == "confirmed"
    assert db_session.scalar(select(Product.canonical_name)) == "语音新品霜"
    assert db_session.scalar(select(func.count(LedgerEntry.id))) == 1

    retried = conversation_service.chat_turn(
        db_session,
        ChatTurnRequest(
            text="确认", request_id="request-voice-confirm-product-retry",
            idempotency_key="voice-confirm-product-key", device_id="phone",
        ),
        now=NOW,
    )
    assert retried["status"] == "confirmed"
    assert retried["idempotent_replay"] is True
    assert db_session.scalar(select(func.count(LedgerEntry.id))) == 1


def test_evaluation_fact_cases_extract_multiple_intolerance_and_observation(db_session):
    seed_customer(db_session)
    multiple = chat(db_session, "甲姐皮肤比较敏感，还经常长痘。", "eval-fac-001")["proposal"]
    fact_types = {a["fact_type"] for a in multiple["actions"] if a["type"] == "upsert_customer_fact"}
    assert fact_types == {"skin_sensitivity", "acne_tendency"}

    # 先取消，避免下一条语音命令误编辑上一张 PendingAction。
    stage3_proposal_service.cancel(
        db_session, multiple["id"],
        ProposalCancelRequest(idempotency_key="cancel-eval-fac-001", device_id="phone"),
        now=NOW,
    )
    intolerance = chat(db_session, "甲姐说用了含香精的东西会不舒服。", "eval-fac-002")["proposal"]
    action = next(a for a in intolerance["actions"] if a["type"] == "upsert_customer_fact")
    assert action["fact_type"] == "ingredient_intolerance"
    assert action["sensitivity_level"] == "sensitive"

    stage3_proposal_service.cancel(
        db_session, intolerance["id"],
        ProposalCancelRequest(idempotency_key="cancel-eval-fac-002", device_id="phone"),
        now=NOW,
    )
    observation = chat(db_session, "甲姐今天脸有点红，看着像敏感肌。", "eval-fac-003")["proposal"]
    action = next(a for a in observation["actions"] if a["type"] == "upsert_customer_fact")
    assert action["fact_type"] == "observation"
    assert action["confidence"] < 0.85


def test_voice_delete_existing_fact_only_creates_retraction_after_confirm(db_session):
    seed_customer(db_session)
    proposal = chat(db_session, "甲姐皮肤敏感。", "fact-to-delete")["proposal"]
    confirm(db_session, proposal, "fact-to-delete")
    current = db_session.scalar(select(CustomerFact).where(CustomerFact.confirmation_status == "confirmed"))

    deletion = chat(db_session, "把甲姐的敏感标签删掉，她说不是敏感。", "delete-fact")["proposal"]
    action = next(a for a in deletion["actions"] if a["type"] == "delete_customer_fact")
    assert action["fact_id"] == current.id
    db_session.refresh(current)
    assert current.valid_to is None
    confirm(db_session, deletion, "delete-fact")
    db_session.refresh(current)
    assert current.valid_to is not None
    retraction = db_session.scalar(select(CustomerFact).where(CustomerFact.confirmation_status == "retracted"))
    assert retraction.supersedes_id == current.id


def test_product_purchase_parser_handles_chinese_quantity_unit():
    parsed = product_resolution_service.extract_product_purchase("小红买了一盒雪绒精华，288")
    assert parsed == {"query": "雪绒精华", "quantity": 1}
