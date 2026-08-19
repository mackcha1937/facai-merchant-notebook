"""套餐卡相关请求模型。价格单位为“分”。"""
from pydantic import BaseModel


class PackageCreate(BaseModel):
    service_id: int
    total_count: int
    price_cents: int | None = None
    purchased_on: str | None = None


class PackageUpdate(BaseModel):
    service_id: int | None = None
    total_count: int | None = None
    used_count: int | None = None
    price_cents: int | None = None
    purchased_on: str | None = None
    status: str | None = None  # active / exhausted / inactive
