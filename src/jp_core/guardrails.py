"""Composable Japanese generation guardrails."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable

from jp_core import furigana, text


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    severity: str = "error"
    location: str | None = None


Rule = Callable[[str], Iterable[Diagnostic]]


@dataclass
class Policy:
    name: str
    rules: list[Rule] = field(default_factory=list)

    def check(self, value: str) -> list[Diagnostic]:
        return [problem for rule in self.rules for problem in rule(value)]

    def require(self, value: str) -> None:
        errors = [item for item in self.check(value) if item.severity == "error"]
        if errors:
            raise ValueError("; ".join(f"{item.code}: {item.message}" for item in errors))


def require_japanese(value: str) -> list[Diagnostic]:
    if text.contains_japanese(value):
        return []
    return [Diagnostic("japanese.required", "text contains no Japanese")]


def max_length(limit: int) -> Rule:
    def check(value: str) -> list[Diagnostic]:
        if len(furigana.strip(value)) <= limit:
            return []
        return [Diagnostic("length.maximum", f"text exceeds {limit} characters")]
    return check


def allowed_vocabulary(words: Iterable[str]) -> Rule:
    allowed = set(words)

    def check(value: str) -> list[Diagnostic]:
        unknown = sorted({token.base for token in furigana.parse(value) if token.annotated and token.base not in allowed})
        return [Diagnostic("vocabulary.unknown", f"unapproved annotated term: {word}") for word in unknown]
    return check


def require_furigana_for_kanji(value: str) -> list[Diagnostic]:
    annotated = "".join(token.base for token in furigana.parse(value) if token.annotated)
    plain = furigana.strip(value)
    missing = sorted(set(text.KANJI_RE.findall(plain)) - set(annotated))
    return [Diagnostic("furigana.missing", f"missing reading for {char}") for char in missing]
