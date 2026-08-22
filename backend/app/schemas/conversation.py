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


class ProposalRegenerateRequest(BaseModel):
    request_id: str = Field(min_length=8, max_length=64)
    idempotency_key: str = Field(min_length=8, max_length=128)
    device_id: str = Field(default="web", min_length=1, max_length=100)


class ProposalCancelRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128)
    device_id: str = Field(default="web", min_length=1, max_length=100)
