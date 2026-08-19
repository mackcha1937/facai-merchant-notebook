"""提示词管理请求模型。"""
from pydantic import BaseModel


class PromptSaveRequest(BaseModel):
    content: str
