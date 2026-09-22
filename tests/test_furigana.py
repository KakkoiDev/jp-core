"""Golden-file tests: extraction must not change how published cards render.

The fixtures were captured from the pre-extraction implementations by
capture_golden.py, over 4464 distinct bracketed values pulled from both repos'
real CSVs plus 21 hand-written edge cases. A failure here means jpanki would
alter the rendering of cards that are already in users' collections.

The one sanctioned divergence is documented in KNOWN_DIVERGENCE below.
"""
import re
import json
from pathlib import Path

import pytest

from jp_core import furigana

GOLDEN = json.loads(
    (Path(__file__).parent / "fixtures" / "golden_furigana.json").read_text(encoding="utf-8")
)
ENTRIES = GOLDEN["entries"]

# minihongo's to_ruby_html omitted 々 from its character class, so a base form
# ending in the repetition mark kept its literal brackets instead of taking
# ruby. jpanki uses the superset, which fixes that. Verified safe: minihongo's
# only bracketed 々 is in comprehension.csv, which the Anki build never reads,
# so no published minihongo card changes. nihongo-it already had the superset.
KNOWN_DIVERGENCE = set(GOLDEN["_ruby_divergence"])

# An empty 【】 is an annotation with no reading in it. Both source projects let
# it through every renderer verbatim, so a card showed 人【】 and the voice read
# the brackets aloud. jp-core drops it — the same leak, and the same fix, as the
# repetition mark above. These are the only rows affected.
STRAY_DIVERGENCE = set(GOLDEN["_stray_divergence"])


def assert_no_brackets(got, text):
    assert "【" not in got and "】" not in got, f"{text!r} leaked a bracket: {got!r}"

# Both source projects kept these lists at module scope; jpanki takes them as
# parameters. The captured values are pinned here so the tests exercise the same
# configuration the originals shipped with.
NIT_TTS_OVERRIDES = set(GOLDEN["_nit_tts_kanji_overrides"])
MH_KEEP_KANJI = set(GOLDEN["_mh_keep_kanji"])


def ids_for(entries):
    return [e["text"][:40] or "<empty>" for e in entries]


@pytest.mark.parametrize("entry", ENTRIES, ids=ids_for(ENTRIES))
def test_to_ruby_matches_nihongo_it(entry):
    """nihongo-it's renderer already used the superset class — match it exactly."""
    if entry["text"] in STRAY_DIVERGENCE:
        return assert_no_brackets(furigana.to_ruby(entry["text"]), entry["text"])
    assert furigana.to_ruby(entry["text"]) == entry["nit_to_ruby_html"]


@pytest.mark.parametrize("entry", ENTRIES, ids=ids_for(ENTRIES))
def test_to_ruby_matches_minihongo_except_known_divergence(entry):
    text = entry["text"]
    got = furigana.to_ruby(text)
    if text in STRAY_DIVERGENCE:
        return assert_no_brackets(got, text)
    if text in KNOWN_DIVERGENCE:
        # Diverges by design, and only by gaining ruby it should have had.
        assert got != entry["mh_to_ruby_html"]
        assert "々【" not in got, "the repetition mark should no longer leak brackets"
    else:
        assert got == entry["mh_to_ruby_html"]


@pytest.mark.parametrize("entry", ENTRIES, ids=ids_for(ENTRIES))
def test_strip_matches_minihongo(entry):
    if entry["text"] in STRAY_DIVERGENCE:
        return assert_no_brackets(furigana.strip(entry["text"]), entry["text"])
    assert furigana.strip(entry["text"]) == entry["mh_strip_furigana"]


@pytest.mark.parametrize("entry", ENTRIES, ids=ids_for(ENTRIES))
def test_to_reading_matches_minihongo(entry):
    """to_reading with no keep-list is minihongo's furigana_to_reading."""
    text = entry["text"]
    got = furigana.to_reading(text)
    if text in STRAY_DIVERGENCE:
        return assert_no_brackets(got, text)
    if text in KNOWN_DIVERGENCE:
        pytest.skip("々 handling diverges by design; covered above")
    assert got == entry["mh_furigana_to_reading"]


@pytest.mark.parametrize("entry", ENTRIES, ids=ids_for(ENTRIES))
def test_keep_base_matches_nihongo_it_with_overrides(entry):
    """keep_base reproduces extract_furigana as nihongo-it actually configures it."""
    got = furigana.keep_base(entry["text"], overrides=NIT_TTS_OVERRIDES)
    if entry["text"] in STRAY_DIVERGENCE:
        return assert_no_brackets(got, entry["text"])
    assert got == entry["nit_extract_furigana"]


@pytest.mark.parametrize("entry", ENTRIES, ids=ids_for(ENTRIES))
def test_keep_base_matches_nihongo_it_without_overrides(entry):
    """And with the override set empty, isolating the base substitution."""
    got = furigana.keep_base(entry["text"])
    if entry["text"] in STRAY_DIVERGENCE:
        return assert_no_brackets(got, entry["text"])
    assert got == entry["nit_extract_furigana_no_overrides"]


# ── behaviour tests, independent of the fixtures ────────────────────


def test_parse_round_trips_to_strip():
    text = "あの人【ひと】は誰【だれ】？"
    assert "".join(t.base for t in furigana.parse(text)) == furigana.strip(text)


def test_parse_tokenises():
    assert furigana.parse("あの人【ひと】は") == [
        furigana.Token("あの"),
        furigana.Token("人", "ひと"),
        furigana.Token("は"),
    ]


def test_parse_empty():
    assert furigana.parse("") == []


@pytest.mark.parametrize("malformed", ["人【", "人【】", "【ひと】", "人", ""])
def test_malformed_never_raises(malformed):
    furigana.parse(malformed)
    furigana.to_ruby(malformed)
    furigana.strip(malformed)
    furigana.to_reading(malformed)
    furigana.keep_base(malformed)


def test_repetition_mark_takes_ruby():
    assert furigana.to_ruby("徐々【じょじょ】") == "<ruby>徐々<rt>じょじょ</rt></ruby>"


def test_normalize_removes_redundant_kana_annotation():
    text = "これはテスト【てすと】です、うまくいっています。日本【にほん】です。"
    assert furigana.normalize(text) == "これはテストです、うまくいっています。日本【にほん】です。"
    assert furigana.normalize("これ【これ】はテスト【てすと】です") == "これはテストです"


def test_only_the_kanji_run_takes_ruby():
    """Kana preceding a kanji run stays outside the <ruby> element."""
    assert furigana.to_ruby("ぶどう酒【ぶどうしゅ】") == "ぶどう<ruby>酒<rt>ぶどうしゅ</rt></ruby>"


def test_to_reading_keep_is_per_character():
    """A compound containing a kept character is kept whole (TTS mispronounces はは)."""
    assert furigana.to_reading("母【はは】", keep={"母"}) == "母"
    assert furigana.to_reading("人【ひと】", keep={"母"}) == "ひと"


def test_keep_base_overrides_match_whole_run():
    """Overriding 生 must not disturb 発生 — the reason this matches whole runs."""
    assert furigana.keep_base("生【なま】", overrides={"生"}) == "なま"
    assert furigana.keep_base("発生【はっせい】", overrides={"生"}) == "発生"


def test_to_reading_clean_drops_punctuation():
    assert furigana.to_reading("あの人【ひと】は誰【だれ】？", clean=True) == "あのひとはだれ"


@pytest.mark.parametrize(
    "text,expected",
    [("ひと", True), ("カタカナ", True), ("コーヒー", True), ("人", False), ("hito", False), ("", False)],
)
def test_is_kana(text, expected):
    assert furigana.is_kana(text) is expected


def test_annotations_extracts_pairs():
    assert furigana.annotations("あの人【ひと】は誰【だれ】？") == [("人", "ひと"), ("誰", "だれ")]


@pytest.mark.parametrize("malformed", ["人【】", "人【 】", "これ【】はテスト"])
def test_empty_annotation_never_reaches_a_renderer(malformed):
    """A reading the model declined to supply must not become visible output."""
    for render in (furigana.to_ruby, furigana.strip, furigana.to_reading, furigana.keep_base, furigana.normalize):
        got = render(malformed)
        assert "【" not in got and "】" not in got, f"{render.__name__} leaked {got!r}"


def test_empty_annotation_does_not_disturb_a_real_reading():
    text = "これ【】はテスト文【ぶん】です"
    assert furigana.to_ruby(text) == "これはテスト<ruby>文<rt>ぶん</rt></ruby>です"
    assert furigana.strip(text) == "これはテスト文です"
    assert furigana.to_reading(text) == "これはテストぶんです"
    assert furigana.normalize(text) == "これはテスト文【ぶん】です"



# --- render and to_mkdocs_ruby, over the same corpus --------------------------
#
# Both are new, and both walk the notation, so the cheapest way to trust them is
# the 4485 real bracketed values already captured above rather than a handful of
# invented ones.


@pytest.mark.parametrize("text", [entry["text"] for entry in ENTRIES])
def test_render_round_trips_through_parse(text):
    """parse then render is the identity, malformed input included.

    Not `normalize`: parse deliberately keeps a stray bracket verbatim in a
    plain token, so 'API【エーピーアイ】' survives the round trip although
    normalize would strip it. That is the guarantee reading.annotate depends on
    when it reassembles a sentence around annotations already in it.
    """
    assert furigana.render(furigana.parse(text)) == text


@pytest.mark.parametrize("text", [entry["text"] for entry in ENTRIES])
def test_mkdocs_ruby_annotates_exactly_what_ruby_does(text):
    """The two renderers must disagree about nothing except their output
    syntax. Whatever one cannot annotate — a reading with no base form in
    front of it, an unclosed bracket — the other leaves alone identically."""
    leftover = re.compile(r"\u3010[^\u3011]*\u3011")
    assert leftover.findall(furigana.to_mkdocs_ruby(text)) == leftover.findall(furigana.to_ruby(text))


def test_mkdocs_ruby_braces_only_multi_character_bases():
    assert furigana.to_mkdocs_ruby("人【ひと】") == "人(ひと)"
    assert furigana.to_mkdocs_ruby("日本【にほん】") == "{日本(にほん)}"
    assert furigana.to_mkdocs_ruby("徐々【じょじょ】") == "{徐々(じょじょ)}"


def test_mkdocs_ruby_drops_an_empty_annotation():
    assert furigana.to_mkdocs_ruby("人【】") == "人"


def test_mkdocs_ruby_leaves_source_parentheses_alone():
    """The corpus has explanatory text with its own parentheses in it. They are
    not annotations and must survive untouched — which is also why this
    rendering is for documentation sites and the bracketed form stays canonical."""
    text = "する事【こと】がしたい (始【はじ】め + たい)"
    assert furigana.to_mkdocs_ruby(text) == "する事(こと)がしたい (始(はじ)め + たい)"


def test_render_writes_an_empty_reading_bare():
    """Nothing render produces should need normalizing afterwards."""
    assert furigana.render([furigana.Token("人", ""), furigana.Token("です")]) == "人です"
    assert furigana.render([furigana.Token("人", "ひと")]) == "人【ひと】"
