"""Shared mechanics for generating Japanese-language Anki decks.

Extracted from minihongo and nihongo-it-anki, which had independently converged
on the same furigana notation, the same card CSS, the same TTS voices and the
same genanki patterns without sharing any code.

The library owns plumbing. It does not own card templates or content schemas —
those are pedagogy, and each consumer keeps its own.

`tts` is not imported here: it needs the `audio` extra, and a consumer that only
builds decks should not have to install edge-tts. Import it directly.
"""
from jp_core import (
    agent,
    anki,
    corpus,
    furigana,
    guardrails,
    ids,
    model,
    pipeline,
    reading,
    release,
    romaji,
    speech,
    text,
    theme,
    validate,
    web,
)
from jp_core.model import NoteSpec, Package, build_deck, build_model, force_style, note_guid, sound_ref, subdeck

__all__ = [
    "furigana",
    "text",
    "corpus",
    "speech",
    "web",
    "guardrails",
    "pipeline",
    "agent",
    "anki",
    "ids",
    "model",
    "reading",
    "release",
    "romaji",
    "theme",
    "validate",
    # The handful of model helpers used on every build path.
    "NoteSpec",
    "Package",
    "build_deck",
    "build_model",
    "force_style",
    "note_guid",
    "sound_ref",
    "subdeck",
]
__version__ = "0.2.0"
