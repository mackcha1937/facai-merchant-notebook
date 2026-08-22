"""语音转写（Speech-to-Text）适配器包。"""
from app.infrastructure.stt.base import SpeechToTextAdapter, TranscriptionResult, SttError
from app.infrastructure.stt.mock import MockSpeechToTextAdapter

__all__ = ["SpeechToTextAdapter", "TranscriptionResult", "SttError", "MockSpeechToTextAdapter"]
