import pytest

from jp_core import reading


def test_is_hiragana():
    assert reading.is_hiragana("き")
    assert not reading.is_hiragana("木")


def test_generation_requires_optional_dependency_or_annotates():
    try:
        result = reading.annotate("日本", overrides={"日": "にち"})
    except RuntimeError as exc:
        assert "jp-core[generation]" in str(exc)
    else:
        assert result.startswith("{日本(")


def test_preserves_existing_annotation_when_generator_available():
    pytest.importorskip("pykakasi")
    assert reading.annotate("日本(にほん)") == "日本(にほん)"
