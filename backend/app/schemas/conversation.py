"""阶段3会话与统一 Proposal API 请求模型。"""
from pydantic import BaseModel, Field


class ChatTurnRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    request_id: str = Field(min_length=8, max_length=64)
    idempotency_key: str = Field(min_length=8, max_length=128)
    device_id: str = Field(default="web", min_length=1, max_length=100)


class ProposalConfirmRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    device_id: str = Field(default="web", min_length=1, max_length=100)
    data_version: int = Field(ge=1)


class ProposalEditRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    data_version: int = Field(ge=1)
    occurred_on: str | None = None
    quantities: dict[str, int] = Field(default_factory=dict)
    remove_action_indexes: list[int] = Field(default_factory=list)


class ProposalRegenerateRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=64)
    idempotency_key: str = Field(min_length=8, max_length=128)
    device_id: str = Field(default="web", min_length=1, max_length=100)


class ProposalCancelRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    device_id: str = Field(default="web", min_length=1, max_length=100)


class ProductResolveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=100)
    specification: str | None = Field(default=None, max_length=100)


class ProductResolutionChoiceRequest(BaseModel):
    data_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=128)
    product_id: int | None = None
    create_new: bool = False
    canonical_name: str | None = Field(default=None, max_length=200)
    brand: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    specification: str | None = Field(default=None, max_length=100)


class ProductDraftProposalRequest(BaseModel):
    canonical_name: str = Field(min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    specification: str | None = Field(default=None, max_length=100)
    aliases: list[str] = Field(default_factory=list, max_length=20)
    request_id: str = Field(min_length=8, max_length=64)
    idempotency_key: str = Field(min_length=8, max_length=128)


class ProductMergeProposalRequest(BaseModel):
    source_product_id: int
    target_product_id: int
    request_id: str = Field(min_length=8, max_length=64)
    idempotency_key: str = Field(min_length=8, max_length=128)


class CustomerFactProposalItem(BaseModel):
    fact_type: str = Field(min_length=1, max_length=50)
    display_value: str = Field(min_length=1, max_length=500)
    evidence_text: str = Field(min_length=1, max_length=2000)
    confidence: float | None = Field(default=None, ge=0, le=1)
    sensitivity_level: str = Field(default="normal", pattern="^(normal|sensitive)$")


class CustomerFactProposalRequest(BaseModel):
    facts: list[CustomerFactProposalItem] = Field(min_length=1, max_length=20)
    request_id: str = Field(min_length=8, max_length=64)
    idempotency_key: str = Field(min_length=8, max_length=128)
