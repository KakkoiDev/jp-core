"""End-to-end tests for SCENARIOS.md: one test per Python scenario, named after its title.

Each test uses JP Core the way an application does, through its public modules, with real files in a scratch
folder (pytest's tmp_path). Network services have stand-ins: an Edge TTS module that counts requests and a `gh`
script on PATH. Offline.
"""
import asyncio
import csv
import json
import os
import sqlite3
import stat
import sys
import types
import zipfile
from pathlib import Path

import genanki
import pytest

from jp_core import agent, anki, corpus, furigana, guardrails, ids, pipeline, reading, release, romaji, speech, text, theme, validate, web

FIELDS = ["Japanese", "English"]
TEMPLATE = [{"name": "Read", "qfmt": "{{Japanese}}", "afmt": "{{FrontSide}}<hr>{{English}}"}]


def register(tmp_path: Path, body: str) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "ids.toml"
    path.write_text(body, encoding="utf-8")
    return path


def build_deck(tmp_path: Path, rows: list[tuple[str, str, str]], *, name: str = "Scenario::01 Basics", out: str = "deck.apkg") -> Path:
    """The consumer's build: registered IDs, one note type, notes keyed by row ID, one .apkg."""
    registry = register(tmp_path, "[scenario]\nmodel_ids = [1990000001]\ndeck_base_id = 1990001000\n")
    registration = anki.for_deck("scenario", registry)
    model = anki.build_model(anki.NoteSpec("Scenario note", registration.model_id, FIELDS, TEMPLATE))
    deck = anki.build_deck(registration.deck_id(1), name)
    for row_id, japanese, english in rows:
        deck.add_note(genanki.Note(model=model, fields=[japanese, english], guid=anki.note_guid("scenario", row_id)))
    package = anki.Package()
    package.add_deck(deck)
    return package.write(tmp_path / out)


def notes_in(apkg: Path) -> list[tuple[str, str]]:
    with zipfile.ZipFile(apkg) as archive:
        database = apkg.with_suffix(".anki2")
        database.write_bytes(archive.read("collection.anki2"))
    with sqlite3.connect(database) as connection:
        return connection.execute("select guid, flds from notes order by id").fetchall()


# Anki decks

def test_build_an_anki_deck_file_from_notes(tmp_path):
    # Given a registered deck and a two-field note type / When I build it with two notes
    apkg = build_deck(tmp_path, [("r1", "本【ほん】です。", "It is a book."), ("r2", "駅【えき】です。", "It is a station.")])
    # Then the .apkg holds both notes under the registered deck ID and name
    assert apkg.is_file()
    notes = notes_in(apkg)
    assert [fields.split("\x1f") for _, fields in notes] == [["本【ほん】です。", "It is a book."], ["駅【えき】です。", "It is a station."]]
    assert release.deck_names(apkg)[1990001001] == "Scenario::01 Basics"


def test_correcting_a_gloss_keeps_the_note_s_identity(tmp_path):
    first = build_deck(tmp_path / "a", [("r1", "本【ほん】です。", "It is a bok.")])
    second = build_deck(tmp_path / "b", [("r1", "本【ほん】です。", "It is a book.")])
    (guid_before, fields_before), = notes_in(first)
    (guid_after, fields_after), = notes_in(second)
    assert fields_before != fields_after
    assert guid_before == guid_after


def test_two_files_claiming_one_media_name_are_refused(tmp_path):
    (tmp_path / "one").mkdir()
    (tmp_path / "two").mkdir()
    first, second = tmp_path / "one/a.mp3", tmp_path / "two/a.mp3"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    package = anki.Package()
    package.add_media(first)
    with pytest.raises(ValueError) as refused:
        package.add_media(second)
    assert str(first) in str(refused.value) and str(second) in str(refused.value)


def test_two_decks_sharing_an_id_range_are_refused(tmp_path):
    registry = ids.load(register(tmp_path, "[first]\nmodel_ids = [1]\ndeck_base_id = 5000\n\n"
                                           "[second]\nmodel_ids = [2]\ndeck_base_id = 5005\n"))
    with pytest.raises(ids.IdCollision) as refused:
        ids.assert_unique(registry)
    assert "'first'" in str(refused.value) and "'second'" in str(refused.value)


# Furigana and text

def test_generate_furigana_for_a_sentence():
    annotated = reading.annotate("日本語【にほんご】を勉強します。一階にあります。")
    assert annotated == "日本語【にほんご】を勉強【べんきょう】します。一階【いっかい】にあります。"
    assert furigana.strip(annotated) == "日本語を勉強します。一階にあります。"


def test_render_one_annotation_for_a_card_a_docs_site_and_plain_text():
    assert furigana.to_ruby("日本語【にほんご】") == "<ruby>日本語<rt>にほんご</rt></ruby>"
    assert furigana.to_mkdocs_ruby("日本語【にほんご】") == "{日本語(にほんご)}"
    assert furigana.strip("日本語【にほんご】") == "日本語"


def test_ruby_html_shows_readings_and_escapes_markup():
    assert web.ruby_html("<b>日本語【にほんご】") == "&lt;b&gt;<ruby>日本語<rt>にほんご</rt></ruby>"


def test_turn_kana_into_romaji_for_a_filename():
    assert romaji.filename("人【ひと】", prefix="w") == "w_hito"
    assert romaji.filename("東京【とうきょう】駅【えき】") == "toukyoueki"


def test_split_japanese_text_into_sentences():
    paragraph = "今日は晴れです。明日は雨ですか？　はい!"
    assert text.sentences(paragraph) == ["今日は晴れです。", "明日は雨ですか？", "はい!"]
    assert text.script_counts("日本語のカタカナ") == {"kanji": 3, "hiragana": 1, "katakana": 4}


# Corpus, guardrails and pipelines

def test_a_collection_resolves_its_sentences_from_a_saved_corpus(tmp_path):
    source = corpus.Provenance("scenario", license="CC0", locator="lesson-1")
    first = corpus.Sentence(corpus.sentence_id("demo", "1"), "本【ほん】です。", "It is a book.", provenance=source)
    second = corpus.Sentence(corpus.sentence_id("demo", "2"), "駅【えき】です。", "It is a station.", tags=("place",))
    saved = corpus.Corpus([first, second]).to_json(tmp_path / "corpus.json")
    loaded = corpus.Corpus.from_json(saved)
    lesson = corpus.Collection("lesson-1", "First lesson", [corpus.CollectionItem(second.id, order=1),
                                                            corpus.CollectionItem(first.id, order=2)])
    resolved = lesson.resolve(loaded)
    assert [sentence.japanese for _, sentence in resolved] == ["駅【えき】です。", "本【ほん】です。"]
    assert resolved[1][1].provenance == source
    assert loaded.query(tags=["place"]) == [second]


def test_a_beginner_policy_refuses_kanji_without_furigana():
    policy = guardrails.Policy("beginner", [guardrails.require_japanese, guardrails.max_length(40),
                                            guardrails.require_furigana_for_kanji])
    assert policy.check("日本語【にほんご】です。") == []
    problems = policy.check("日本語【にほんご】の駅です。")
    assert [(p.code, p.message) for p in problems] == [("furigana.missing", "missing reading for 駅")]
    with pytest.raises(ValueError, match="furigana.missing"):
        policy.require("日本語【にほんご】の駅です。")


def test_a_pipeline_records_what_each_step_did():
    steps = pipeline.Pipeline(pipeline.Step("strip", furigana.strip), pipeline.Step("split", text.sentences, version="2"))
    result = steps.run("本【ほん】です。駅【えき】です。")
    assert result.value == ["本です。", "駅です。"]
    assert [(m["step"], m["version"]) for m in result.manifest] == [("strip", "1"), ("split", "2")]
    assert result.manifest[0]["output"] == result.manifest[1]["input"]
    assert all(len(m["input"]) == 64 and len(m["output"]) == 64 for m in result.manifest)


# Speech

def test_a_registered_tts_provider_writes_the_clip(tmp_path):
    received = []

    class ApplicationProvider:
        async def synthesize(self, request):
            received.append(request.spoken_text())
            request.output.write_bytes(b"ID3 stand-in clip")
            return request.output

    providers = speech.ProviderRegistry()
    providers.register_tts("application-provider", ApplicationProvider())
    request = speech.SynthesisRequest(text="提出【ていしゅつ】します。", voice=speech.Voice("ja-JP-NanamiNeural"),
                                      output=tmp_path / "clip.mp3", pronunciation_overrides={"提出": "ていしゅつ"})
    clip = asyncio.run(providers.tts("application-provider").synthesize(request))
    assert clip.read_bytes() == b"ID3 stand-in clip"
    assert received == [request.spoken_text()] and "【" not in received[0]
    assert providers.capabilities() == {"tts": ["application-provider"], "stt": []}


def test_synthesize_repeated_text_once(tmp_path, monkeypatch):
    requests = []

    class Communicate:
        def __init__(self, words, voice):
            self.words, self.voice = words, voice

        async def save(self, path):
            requests.append(self.words)
            Path(path).write_bytes(f"clip:{self.words}".encode())

    monkeypatch.setitem(sys.modules, "edge_tts", types.SimpleNamespace(Communicate=Communicate))
    from jp_core import tts
    jobs = [tts.Job("本です。", tmp_path / "a.mp3"), tts.Job("駅です。", tmp_path / "b.mp3"), tts.Job("本です。", tmp_path / "c.mp3")]
    asyncio.run(tts.Synthesizer(delay=0, postprocess=False).run(jobs))
    assert [job.output.read_text(encoding="utf-8") for job in jobs] == ["clip:本です。", "clip:駅です。", "clip:本です。"]
    assert requests == ["本です。", "駅です。"]


def test_compare_a_spoken_transcript_with_the_expected_sentence():
    assert speech.compare_transcript("本【ほん】を読【よ】みます。", "本を読みます")
    assert not speech.compare_transcript("本【ほん】を読【よ】みます。", "本を書きます")


# Validation and release

def test_a_csv_with_a_missing_column_is_refused(tmp_path):
    path = tmp_path / "notes.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerows([["id", "japanese"], ["1", "本【ほん】"]])
    report = validate.check_columns(validate.load_rows(path), ["id", "japanese", "translation"], where="notes.csv")
    assert not report.ok
    assert "translation" in report.render()


def test_an_edited_input_makes_the_released_deck_stale(tmp_path):
    source = tmp_path / "notes.csv"
    source.write_text("id,japanese\n1,本【ほん】\n", encoding="utf-8")
    stored = validate.write_manifest([source], tmp_path / "manifest.json", extra={"jp-core": "0.2.0"})
    assert validate.check_fresh([source], stored, extra={"jp-core": "0.2.0"}).ok
    source.write_text("id,japanese\n1,本【ほん】\n2,駅【えき】\n", encoding="utf-8")
    report = validate.check_fresh([source], stored, extra={"jp-core": "0.2.0"})
    assert report.errors == [f"{source} changed since the last release"]


def test_publish_a_deck_as_a_new_github_release(tmp_path, monkeypatch):
    apkg = build_deck(tmp_path, [("r1", "本【ほん】です。", "It is a book.")])
    log, bin_dir = tmp_path / "gh.log", tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$*\" >> '{log}'\n"
                  "if [ \"$1 $2\" = 'release view' ]; then echo 'release not found' >&2; exit 1; fi\n", encoding="utf-8")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    release.publish(release.Release(tag="scenario/v1", title="Scenario deck v1", assets=[apkg], notes="First."))
    calls = log.read_text(encoding="utf-8").splitlines()
    assert calls[0] == "release view scenario/v1 --json tagName"
    assert calls[1] == f"release create scenario/v1 {apkg} --title Scenario deck v1 --notes First."


def test_a_release_that_renames_a_published_deck_is_refused(tmp_path):
    published = build_deck(tmp_path / "old", [("r1", "本【ほん】です。", "It is a book.")])
    candidate = build_deck(tmp_path / "new", [("r1", "本【ほん】です。", "It is a book.")], name="Scenario::01 Renamed")
    with pytest.raises(release.ReleaseError, match="renamed ID 1990001001"):
        release.assert_deck_names_compatible(published, candidate)


# Discovery and styling

def test_find_the_projects_that_use_a_capability():
    capabilities = agent.capabilities()
    assert capabilities
    examples = agent.find_examples(capabilities[0])
    assert examples and all(capabilities[0] in item["capabilities"] for item in examples)
    assert all(item.get("status") == "consumer" for item in agent.find_examples(capabilities[0], consumers_only=True))


def test_compose_the_card_stylesheet_from_layers():
    mine = ".card .mine { color: red; }"
    css = theme.compose(theme.base(), theme.ruby(), theme.night(), extra=mine)
    for layer in (theme.base(), theme.ruby(), theme.night()):
        assert layer.strip().splitlines()[0].strip() in css
    assert "ruby rt" in css
    assert css.rstrip().endswith(mine)


def test_the_furigana_demo_page_matches_what_jp_core_web_builds():
    """The page the Playwright scenarios open is jp_core.web's output, not a hand-made copy."""
    page = (Path(__file__).parent / "e2e/pages/furigana.html").read_text(encoding="utf-8")
    assert web.ruby_html("日本語【にほんご】を勉強【べんきょう】します。") in page
    assert web.toggle_button() in page
    assert web.FURIGANA_CSS in page and web.FURIGANA_TOGGLE_JS in page
