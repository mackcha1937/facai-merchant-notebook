"""账本记录相关请求模型（阶段1支持手动记录一次性服务、商品购买和手动核销）。"""
from pydantic import BaseModel


class LedgerEntryCreate(BaseModel):
    entry_type: str  # one_time_service / product_purchase / package_consumption
    service_id: int | None = None
    package_id: int | None = None
    product_name: str | None = None
    quantity: int = 1
    price_cents: int | None = None
    occurred_on: str | None = None
