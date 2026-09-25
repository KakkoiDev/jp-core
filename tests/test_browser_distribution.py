"""browser/jp-core.js must decide the same things the Python modules decide.

The browser distribution exists because a static PWA cannot run Python, not
because it is allowed its own opinions. Nothing here runs Node: these read the
JavaScript as text and compare the rules it encodes against the Python ones, so
the guard costs nothing in CI and still fails the moment the two drift.

Drift here is silent by construction. A kanji class that disagrees means one
side brackets a run the other drops as a stray, and the reading vanishes from
the page with no error anywhere.
"""
import json
import re
from pathlib import Path

from jp_core import furigana, reading

SOURCE = (Path(__file__).resolve().parents[1] / "browser" / "jp-core.js").read_text(encoding="utf-8")
GOLDEN = json.loads(
    (Path(__file__).parent / "fixtures" / "golden_furigana.json").read_text(encoding="utf-8")
)


def unescape(pattern: str) -> str:
    """Turn JavaScript \\uXXXX and \\u{XXXXX} escapes into the characters they name."""
    pattern = re.sub(r"\\u\{([0-9a-fA-F]+)\}", lambda m: chr(int(m.group(1), 16)), pattern)
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), pattern)


def character_class(name: str) -> str:
    """The first bracketed class in a declaration, anchors and quantifiers aside."""
    match = re.search(rf"^(?:export )?const {name} = /[^\[]*\[([^\]]*)\]", SOURCE, re.MULTILINE)
    assert match, f"{name} is not declared in browser/jp-core.js"
    return unescape(match.group(1))


def test_kanji_class_matches_the_canonical_base_chars():
    """Every code point one side calls a base character, the other must too."""
    js = re.compile(f"[{character_class('KANJI')}]")
    python = re.compile(f"[{furigana.BASE_CHARS}]")
    # The supplementary planes are scanned too. They were not, once, and that
    # is how a class stopping at U+9FFF kept agreeing with itself while 𠮟
    # (U+20B9F, joyo) fell outside both.
    disagreements = [
        chr(point)
        for span in (range(0x3000, 0xA000), range(0x20000, 0x31350))
        for point in span
        if bool(js.match(chr(point))) != bool(python.match(chr(point)))
    ]
    assert not disagreements, f"kanji class differs on {disagreements[:10]}"


def test_base_class_covers_the_joyo_kanji_outside_the_bmp():
    """𠮟 is on the joyo list and lives at U+20B9F."""
    python = re.compile(f"[{furigana.BASE_CHARS}]")
    js = re.compile(f"[{character_class('KANJI')}]")
    assert python.match("𠮟")
    assert js.match("𠮟")


def test_reading_class_matches():
    js = re.compile(f"^[{character_class('KANA')}]+$")
    for kana in ["ひらがな", "きょう", "こーひー", "ぁ"]:
        assert js.match(kana), kana
    for other in ["カタカナ", "eki", "えき です", "駅", ""]:
        assert not js.match(other), other


def test_pronunciation_overrides_are_identical():
    block = re.search(
        r"export const PRONUNCIATION_OVERRIDES = \{(.*?)\n\};", SOURCE, re.DOTALL
    )
    assert block, "PRONUNCIATION_OVERRIDES is not declared in browser/jp-core.js"
    js = dict(re.findall(r'"([^"]+)":"([^"]+)"', block.group(1)))
    assert js == dict(reading.PRONUNCIATION_OVERRIDES)


def test_browser_distribution_declares_the_current_schema():
    match = re.search(r"export const SCHEMA_VERSION = (\d+);", SOURCE)
    assert match, "SCHEMA_VERSION is not declared in browser/jp-core.js"
    # Bumping the record shape without bringing the browser copy along is the
    # drift that stranded this file at 1 while its consumer moved to 2.
    assert int(match.group(1)) == 2


def js_pattern(name: str) -> re.Pattern:
    """The pattern, whatever flags follow it. `u` is not cosmetic — without it
    \\u{...} is not an escape at all — so the flags are read, not assumed."""
    match = re.search(rf"^const {name} = /(.*)/([a-z]*);$", SOURCE, re.MULTILINE)
    assert match, f"{name} is not declared in browser/jp-core.js"
    assert "g" in match.group(2), f"{name} must be global"
    return re.compile(unescape(match.group(1)))


def test_notation_and_stray_patterns_behave_identically():
    """Compared by what they match, not how they are spelled: the two files list
    the same CJK ranges in a different order, which is allowed, and would make
    a string comparison fail for no reason."""
    samples = [entry["text"] for entry in GOLDEN["entries"]]
    for name, python in [("notation", furigana.NOTATION_RE), ("stray", furigana._BRACKET_RE)]:
        js = js_pattern(name)
        for text in samples:
            assert js.findall(text) == python.findall(text), f"{name} differs on {text!r}"


def test_notation_keeps_a_reading_on_a_supplementary_plane_kanji():
    """𠮟【しか】る used to come back as 𠮟る in both languages: the base class
    stopped at U+9FFF, so `notation` never matched and the bracket was then
    removed as a stray. Silent, and wrong in exactly the way the comment above
    KANJI warns about."""
    text = "𠮟【しか】らないで"
    assert furigana.NOTATION_RE.findall(text) == [("𠮟", "しか")]
    assert js_pattern("notation").findall(text) == [("𠮟", "しか")]
