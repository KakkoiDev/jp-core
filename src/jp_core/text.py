"""Japanese text classification and normalization."""
from __future__ import annotations

import re
import unicodedata

KANJI_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff々]")
HIRAGANA_RE = re.compile(r"[\u3040-\u309f]")
KATAKANA_RE = re.compile(r"[\u30a0-\u30ff]")
JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff々]")
SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[。！？!?])\s*")


def normalize(value: str) -> str:
    """Return canonical Unicode with normalized Japanese whitespace."""
    value = unicodedata.normalize("NFC", value).replace("\u3000", " ")
    return re.sub(r"[ \t]+", " ", value).strip()


def contains_japanese(value: str) -> bool:
    return bool(JAPANESE_RE.search(value))


def script_counts(value: str) -> dict[str, int]:
    return {
        "kanji": len(KANJI_RE.findall(value)),
        "hiragana": len(HIRAGANA_RE.findall(value)),
        "katakana": len(KATAKANA_RE.findall(value)),
    }


def sentences(value: str) -> list[str]:
    """Split Japanese prose without discarding terminal punctuation."""
    return [part.strip() for part in SENTENCE_BOUNDARY_RE.split(value) if part.strip()]
