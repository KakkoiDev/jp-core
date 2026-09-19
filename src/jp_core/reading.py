"""Deterministic Japanese reading generation.

This module owns Japanese-aware token recognition and reading generation.
Consumers remain responsible for their document format and teaching choices.
"""
from __future__ import annotations

import re
from collections.abc import Mapping

KANJI_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]+")


def is_hiragana(char: str) -> bool:
    """Return whether *char* is a hiragana code point."""
    return bool(char) and "\u3040" <= char <= "\u309f"


def annotate(
    text: str,
    *,
    overrides: Mapping[str, str] | None = None,
) -> str:
    """Add mkdocs-ruby-plugin annotations to bare kanji runs.

    Existing parenthesized annotations are preserved. A single kanji followed
    by okurigana is left untouched because an isolated dictionary lookup cannot
    reliably choose its contextual kun reading.
    """
    try:
        import pykakasi
    except ImportError as exc:
        raise RuntimeError(
            "Reading generation requires the jp-core[generation] extra"
        ) from exc

    converter = pykakasi.kakasi()
    forced = dict(overrides or {})

    def replace(match: re.Match[str]) -> str:
        kanji = match.group(0)
        rest = text[match.end() : match.end() + 15]
        if rest.startswith("(") and ")" in rest:
            return kanji
        if len(kanji) == 1:
            following = text[match.end() : match.end() + 1]
            if is_hiragana(following):
                return kanji
            if kanji in forced:
                return f"{kanji}({forced[kanji]})"
        try:
            reading = "".join(item["hira"] for item in converter.convert(kanji))
        except Exception:
            return kanji
        if not reading or reading == kanji:
            return kanji
        return f"{{{kanji}({reading})}}" if len(kanji) > 1 else f"{kanji}({reading})"

    return KANJI_RE.sub(replace, text)
