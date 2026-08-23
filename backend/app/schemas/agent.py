"""Agent 相关请求模型。"""
from pydantic import BaseModel, Field


class InterpretRequest(BaseModel):
    text: str


class FuzzySearchRequest(BaseModel):
    query: str


class NewCustomer(BaseModel):
    display_name: str
    aliases: list[str] = Field(default_factory=list)


class ConfirmCustomer(BaseModel):
    customer_id: int | None = None
    new_customer: NewCustomer | None = None


class ConfirmAction(BaseModel):
    type: str
    service_id: int | None = None
    package_id: int | None = None
    product_name: str | None = None
    product_id: int | None = None
    create_product: bool = False
    canonical_name: str | None = None
    brand: str | None = None
    category: str | None = None
    specification: str | None = None
    aliases: list[str] = Field(default_factory=list)
    source_product_id: int | None = None
    target_product_id: int | None = None
    fact_type: str | None = None
    display_value: str | None = None
    normalized_value: str | None = None
    evidence_text: str | None = None
    confidence: float | None = None
    sensitivity_level: str | None = None
    supersedes_id: int | None = None
    fact_id: int | None = None
    quantity: int | None = None
    price_cents: int | None = None
    total_count: int | None = None
    purchased_on: str | None = None
    occurred_on: str | None = None


class ConfirmRequest(BaseModel):
    customer: ConfirmCustomer | None = None
    actions: list[ConfirmAction] = Field(default_factory=list)


class PrecheckRequest(BaseModel):
    customer: ConfirmCustomer
    actions: list[ConfirmAction] = Field(default_factory=list)
