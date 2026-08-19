"""模型适配器抽象接口。"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ModelCheckResult:
    """连通性检查结果（message 必须已经脱敏）。"""

    success: bool
    configured: bool
    message: str
    model_id: str = ""


class ModelError(Exception):
    """模型调用失败（信息已脱敏）。"""


class ModelAdapter(ABC):
    """所有模型适配器需要实现的统一接口。"""

    @abstractmethod
    def check_connectivity(self) -> ModelCheckResult:
        """执行最小连通性检查，返回脱敏结果。"""
        raise NotImplementedError

    @abstractmethod
    def chat(self, messages: list[dict], temperature: float = 0.0) -> str:
        """发起一次对话补全请求，返回模型回复文本。"""
        raise NotImplementedError
