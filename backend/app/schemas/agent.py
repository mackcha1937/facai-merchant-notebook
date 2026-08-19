"""Agent 相关请求模型。"""
from pydantic import BaseModel


class InterpretRequest(BaseModel):
    text: str


class FuzzySearchRequest(BaseModel):
    query: str
