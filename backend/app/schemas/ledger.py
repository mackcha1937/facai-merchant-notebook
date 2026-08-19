"""账本记录相关请求模型（阶段1仅支持手动记录一次性服务与商品购买）。"""
from pydantic import BaseModel, Field


class LedgerEntryCreate(BaseModel):
    entry_type: str  # one_time_service / product_purchase
    service_id: int | None = None
    product_name: str | None = None
    quantity: int = 1
    price_cents: int | None = None
    occurred_on: str | None = None
