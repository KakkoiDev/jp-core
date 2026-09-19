"""Canonical sentence corpus and provenance models."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from jp_core import furigana


def sentence_id(namespace: str, key: str) -> str:
    """Stable content-independent ID from a corpus namespace and business key."""
    digest = hashlib.sha256(f"{namespace}\x1f{key}".encode()).hexdigest()[:16]
    return f"{namespace}:{digest}"


@dataclass(frozen=True)
class Provenance:
    source: str
    license: str | None = None
    locator: str | None = None


@dataclass(frozen=True)
class Sentence:
    id: str
    japanese: str
    translation: str
    reading: str | None = None
    tags: tuple[str, ...] = ()
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if not self.id or not self.japanese or not self.translation:
            raise ValueError("sentence id, japanese, and translation are required")
        if self.reading is not None and not self.reading.strip():
            raise ValueError("reading must be non-empty when provided")

    @property
    def plain_japanese(self) -> str:
        return furigana.strip(self.japanese)


class Corpus:
    """An indexed collection of canonical sentences."""

    def __init__(self, sentences: Iterable[Sentence] = ()):
        self._items: dict[str, Sentence] = {}
        for sentence in sentences:
            self.add(sentence)

    def add(self, sentence: Sentence) -> None:
        if sentence.id in self._items:
            raise ValueError(f"duplicate sentence id: {sentence.id}")
        self._items[sentence.id] = sentence

    def get(self, sentence_id: str) -> Sentence:
        return self._items[sentence_id]

    def query(self, *, tags: Iterable[str] = (), text: str | None = None) -> list[Sentence]:
        required = set(tags)
        result = []
        for item in self._items.values():
            if required and not required.issubset(item.tags):
                continue
            if text and text not in item.japanese and text not in item.translation:
                continue
            result.append(item)
        return result

    def to_json(self, path: Path) -> Path:
        payload = [asdict(item) for item in self._items.values()]
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path

    @classmethod
    def from_json(cls, path: Path) -> "Corpus":
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = []
        for row in raw:
            provenance = row.get("provenance")
            row["provenance"] = Provenance(**provenance) if provenance else None
            row["tags"] = tuple(row.get("tags", ()))
            items.append(Sentence(**row))
        return cls(items)


@dataclass(frozen=True)
class CollectionItem:
    """Teaching metadata referencing, never copying, a corpus sentence."""
    sentence_id: str
    order: int
    prompt: str | None = None
    hint: str | None = None
    roles: tuple[str, ...] = ()


@dataclass
class Collection:
    id: str
    title: str
    items: list[CollectionItem] = field(default_factory=list)

    def resolve(self, corpus: Corpus) -> list[tuple[CollectionItem, Sentence]]:
        return [(item, corpus.get(item.sentence_id)) for item in sorted(self.items, key=lambda x: x.order)]
