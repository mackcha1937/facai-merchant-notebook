"""阶段7离线测评、人工结果与发布治理请求。"""
from pydantic import BaseModel, Field


class ConfigDraftCreate(BaseModel):
    config_type: str = Field(pattern="^(prompt|rag|recommendation)$")
    content: dict


class EvaluationRunCreate(BaseModel):
    draft_id: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")


class ManualResultsImport(BaseModel):
    csv_text: str = Field(min_length=20, max_length=500_000)


class ReleasePublishRequest(BaseModel):
    draft_id: int = Field(ge=1)
    run_id: int = Field(ge=1)
    confirmation: str = Field(min_length=10, max_length=100)
    expected_data_version: int = Field(ge=1)
    request_id: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")


class ReleaseRollbackRequest(BaseModel):
    release_type: str = Field(pattern="^(prompt|rag|recommendation)$")
    release_id: int = Field(ge=1)
    confirmation: str = Field(min_length=10, max_length=100)
    request_id: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")
