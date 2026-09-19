"""Provider contracts and Japanese speech pipeline primitives."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from jp_core import furigana, text


@dataclass(frozen=True)
class Voice:
    id: str
    language: str = "ja-JP"
    gender: str | None = None


@dataclass(frozen=True)
class SynthesisRequest:
    text: str
    voice: Voice
    output: Path
    pronunciation_overrides: dict[str, str] = field(default_factory=dict)

    def spoken_text(self) -> str:
        result = furigana.keep_base(self.text, overrides=self.pronunciation_overrides)
        return text.normalize(result)

    def cache_key(self) -> str:
        payload = f"{self.spoken_text()}\x1f{self.voice.id}\x1f{self.voice.language}"
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class Transcript:
    text: str
    language: str = "ja-JP"
    confidence: float | None = None


class TTSProvider(Protocol):
    async def synthesize(self, request: SynthesisRequest) -> Path: ...


class STTProvider(Protocol):
    async def transcribe(self, audio: Path, *, language: str = "ja-JP") -> Transcript: ...


def normalize_transcript(value: str) -> str:
    return text.normalize(value).translate(str.maketrans("", "", "、。！？!? "))


def compare_transcript(expected: str, actual: str) -> bool:
    return normalize_transcript(furigana.strip(expected)) == normalize_transcript(actual)


class ProviderRegistry:
    """Explicit provider registry; no imports, credentials, or global discovery."""

    def __init__(self):
        self._tts: dict[str, TTSProvider] = {}
        self._stt: dict[str, STTProvider] = {}

    def register_tts(self, name: str, provider: TTSProvider) -> None:
        self._tts[name] = provider

    def register_stt(self, name: str, provider: STTProvider) -> None:
        self._stt[name] = provider

    def tts(self, name: str) -> TTSProvider:
        return self._tts[name]

    def stt(self, name: str) -> STTProvider:
        return self._stt[name]

    def capabilities(self) -> dict[str, list[str]]:
        return {"tts": sorted(self._tts), "stt": sorted(self._stt)}
