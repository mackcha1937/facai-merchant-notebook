"""阶段6推荐、今日事项、话术与反馈请求结构。"""
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class RecommendationRefreshRequest(BaseModel):
    target_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    request_id: str = Field(min_length=8, max_length=64)


class RecommendationReadRequest(BaseModel):
    data_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=128)


class RecommendationActionRequest(BaseModel):
    action: str = Field(pattern="^(contacted|snoozed|repurchased|not_needed|unsuitable|do_not_recommend|cancelled|allow_recommendation)$")
    data_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=128)
    snoozed_until: datetime | None = None
    feedback_text: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_snooze(self):
        if self.action == "snoozed" and self.snoozed_until is None:
            raise ValueError("稍后处理必须提供绝对时间")
        if self.action != "snoozed" and self.snoozed_until is not None:
            raise ValueError("只有稍后处理可设置时间")
        return self


class MessageRewriteRequest(BaseModel):
    variant: str = Field(pattern="^(shorter|no_purchase)$")
    idempotency_key: str = Field(min_length=8, max_length=128)


class MessageCopyRequest(BaseModel):
    data_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=128)


class RecommendationFeedbackRequest(BaseModel):
    action: str = Field(pattern="^(contacted|snoozed|repurchased|not_needed|unsuitable|do_not_recommend|cancelled|ai_inaccurate)$")
    feedback_text: str | None = Field(default=None, max_length=1000)
    data_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=128)
    request_id: str = Field(min_length=8, max_length=64)
    snoozed_until: datetime | None = None

    @model_validator(mode="after")
    def validate_feedback(self):
        if self.action == "snoozed" and self.snoozed_until is None and not self.feedback_text:
            raise ValueError("稍后处理需要绝对时间或可解析的反馈原文")
        if self.action == "ai_inaccurate" and not self.feedback_text:
            raise ValueError("AI不准确反馈需要说明")
        return self
