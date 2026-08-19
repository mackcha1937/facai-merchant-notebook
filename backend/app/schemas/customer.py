"""客户相关请求模型。"""
from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    display_name: str
    aliases: list[str] = Field(default_factory=list)


class CustomerUpdate(BaseModel):
    display_name: str | None = None
    aliases: list[str] | None = None
