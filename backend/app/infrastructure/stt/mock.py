"""Mock 语音转写适配器（阶段2）。

不连接真实语音服务，不产生供应商费用，不发送真实客户音频。
- audio_ref 在本阶段直接作为“店主说了什么”的演示文本（真实实现里是音频对象引用）；
- 支持转写成功 / 转写失败 / 网络失败三种演示模式；
- 返回结果标记 is_mock=True。
"""
from app.infrastructure.stt.base import (
    SpeechToTextAdapter,
    TranscriptionResult,
    TranscriptionSegment,
    SttError,
)

# 演示用默认转写文本（用于未提供 utterance 时）
DEFAULT_UTTERANCE = "阿珍今天做了一次肩颈按摩"


class MockSpeechToTextAdapter(SpeechToTextAdapter):
    """纯演示实现：echo 音频引用为转写文本，可模拟失败。"""

    def __init__(self, fail_mode: str | None = None):
        # fail_mode: None -> 成功；"transcribe" -> 转写失败；"network" -> 网络失败
        self.fail_mode = fail_mode

    def transcribe(self, audio_ref: str, language: str = "zh-CN") -> TranscriptionResult:
        if self.fail_mode == "network":
            raise SttError("网络失败，请检查连接后重试（Mock）")
        if self.fail_mode == "transcribe":
            raise SttError("语音转写失败，请重试（Mock）")

        text = (audio_ref or "").strip() or DEFAULT_UTTERANCE
        # 低置信片段示例：标记长文本后段（演示用途，不涉及真实音频）
        segments = []
        if len(text) > 8:
            segments.append(TranscriptionSegment(start_ms=0, end_ms=800, text=text[:8], confidence=0.96))
            segments.append(TranscriptionSegment(start_ms=800, end_ms=1400, text=text[8:], confidence=0.72))
        else:
            segments.append(TranscriptionSegment(start_ms=0, end_ms=900, text=text, confidence=0.95))

        return TranscriptionResult(
            transcript=text,
            provider="mock",
            model="mock-stt-v1",
            confidence=0.9,
            segments=segments,
            is_mock=True,
            audio_expires_in_seconds=86400,
        )
