"""语音转写适配器抽象接口。

阶段2只建立接口和Mock实现，不连接真实语音供应商，不产生供应商费用，
不发送真实客户音频。真实实现（如各厂商 STT）在后续阶段接入时必须：
- 音频默认只用于转写与失败重试，开发环境 24 小时自动删除；
- 转写文本必须返回前端并允许店主修改后再进入 /chat/turn；
- 语音与文字走完全相同的意图、Proposal、权限、确认、审计和幂等流程。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TranscriptionSegment:
    """低置信片段按时间段标记，不由模型静默补词。"""

    start_ms: int
    end_ms: int
    text: str
    confidence: float


@dataclass
class TranscriptionResult:
    """转写结果（已脱敏，不含供应商敏感信息）。"""

    transcript: str
    provider: str
    model: str
    confidence: float
    segments: list[TranscriptionSegment] = field(default_factory=list)
    is_mock: bool = False
    audio_expires_in_seconds: int = 86400  # 开发默认 24 小时


class SttError(Exception):
    """语音转写失败（信息已脱敏）。"""


class SpeechToTextAdapter(ABC):
    """所有语音转写适配器需要实现的统一接口。"""

    @abstractmethod
    def transcribe(self, audio_ref: str, language: str = "zh-CN") -> TranscriptionResult:
        """转写一段音频引用，返回可编辑文本与分段置信度。

        不执行任何业务写入。转写失败抛 SttError。
        """
        raise NotImplementedError
