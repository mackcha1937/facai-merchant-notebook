"""服务项目相关请求模型。"""
from pydantic import BaseModel


class ServiceCreate(BaseModel):
    name: str


class ServiceUpdate(BaseModel):
    name: str | None = None
    status: str | None = None  # active / inactive
