"""Stable Anki facade.

Applications should import this module instead of depending on the historical
layout of JP Core's internal model and validation modules.
"""
from jp_core.ids import Registration, for_deck, load
from jp_core.model import (
    NoteSpec,
    Package,
    build_deck,
    build_model,
    force_style,
    note_guid,
    sound_ref,
    subdeck,
)
from jp_core.validate import Report, check_columns, check_fresh, check_media, check_required, check_unique

__all__ = [
    "Registration", "load", "for_deck", "NoteSpec", "Package", "build_deck",
    "build_model", "force_style", "note_guid", "sound_ref", "subdeck",
    "Report", "check_columns", "check_fresh", "check_media", "check_required",
    "check_unique",
]
