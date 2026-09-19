from pathlib import Path

import pytest

from jp_core import agent, corpus, guardrails, pipeline, speech, text, web


def test_text_normalization_and_segmentation():
    assert text.normalize(" 日本語　です ") == "日本語 です"
    assert text.sentences("はい。そうです！") == ["はい。", "そうです！"]
    assert text.script_counts("日本語です") == {"kanji": 3, "hiragana": 2, "katakana": 0}


def test_corpus_collection_references_without_copying(tmp_path: Path):
    item = corpus.Sentence(
        corpus.sentence_id("demo", "one"),
        "日本【にほん】です。",
        "It is Japan.",
        tags=("n5",),
        provenance=corpus.Provenance("demo"),
    )
    source = corpus.Corpus([item])
    collection = corpus.Collection("lesson-1", "Lesson 1", [
        corpus.CollectionItem(item.id, 1, prompt="Read it"),
    ])
    assert collection.resolve(source)[0][1] is item
    path = source.to_json(tmp_path / "corpus.json")
    assert corpus.Corpus.from_json(path).get(item.id) == item


def test_duplicate_sentence_ids_fail():
    item = corpus.Sentence("x", "日本", "Japan")
    with pytest.raises(ValueError, match="duplicate"):
        corpus.Corpus([item, item])


def test_speech_request_and_transcript_comparison(tmp_path: Path):
    request = speech.SynthesisRequest(
        "提出【ていしゅつ】します。",
        speech.Voice("ja-test"),
        tmp_path / "clip.mp3",
        {"提出": "ていしゅつ"},
    )
    assert request.spoken_text() == "ていしゅつします。"
    assert len(request.cache_key()) == 64
    assert speech.compare_transcript("日本【にほん】です。", "日本です")


def test_provider_registry_is_explicit():
    registry = speech.ProviderRegistry()
    marker = object()
    registry.register_tts("test", marker)
    assert registry.tts("test") is marker
    assert registry.capabilities() == {"tts": ["test"], "stt": []}


def test_safe_ruby_and_toggle():
    assert web.ruby_html("<b>人【ひと】</b>") == "&lt;b&gt;<ruby>人<rt>ひと</rt></ruby>&lt;/b&gt;"
    assert "data-jp-core-furigana-toggle" in web.toggle_button(label="Show")


def test_guardrail_policy_returns_structured_diagnostics():
    policy = guardrails.Policy("learner", [
        guardrails.require_japanese,
        guardrails.max_length(4),
        guardrails.require_furigana_for_kanji,
    ])
    problems = policy.check("日本語です")
    assert {problem.code for problem in problems} == {"length.maximum", "furigana.missing"}


def test_pipeline_manifest_is_reproducible():
    process = pipeline.Pipeline(
        pipeline.Step("strip", str.strip),
        pipeline.Step("upper", str.upper),
    )
    first = process.run(" hello ")
    second = process.run(" hello ")
    assert first.value == "HELLO"
    assert first.manifest == second.manifest


def test_agent_router_exposes_real_consumers():
    matches = agent.find_examples("anki-deck-generation", consumers_only=True)
    assert any(item["id"] == "jpanki" for item in matches)
