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
    quantity: int | None = None
    price_cents: int | None = None
    total_count: int | None = None
    purchased_on: str | None = None


class ConfirmRequest(BaseModel):
    customer: ConfirmCustomer
    actions: list[ConfirmAction] = Field(default_factory=list)
