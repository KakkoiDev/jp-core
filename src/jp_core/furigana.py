"""The `漢字【かんじ】` furigana notation: one parser, several renderers.

Both source projects annotate readings inline, writing a base form immediately
followed by its reading in lenticular brackets:

    あの人【ひと】は誰【だれ】？

and then render that per target — ruby HTML for cards, bare kanji for display,
all-kana for text-to-speech. Between them they had four regexes doing this,
with three *different* character classes:

    minihongo to_ruby_html         kanji + ext-A
    minihongo furigana_to_reading  kanji + ext-A
    minihongo text_for_tts         kanji + ext-A + 々
    nihongo-it to_ruby_html        kanji + ext-A + 々
    nihongo-it extract_furigana    kanji + 々          (+ leading digits)

The practical consequence: `徐々【じょじょ】` rendered correctly in some paths
and leaked literal brackets onto the card in others. This module parses the
notation once, into tokens, and renders from those — so a base form is either
annotatable everywhere or nowhere.

The canonical class is the superset (`BASE_CHARS`). Adopting it was verified
against both corpora: it changes nothing in minihongo's Anki-consumed CSVs
(their only bracketed 々 lives in comprehension.csv, which the deck build does
not read) and reproduces nihongo-it's ruby output exactly.
"""
from __future__ import annotations

import re
from typing import Iterable, NamedTuple

# CJK ideographs, CJK ext-A, 々 (the repetition mark, U+3005, as in 徐々), and
# the supplementary planes. 々 belongs here because it is part of the *written*
# base form even though it is not itself an ideograph.
#
# U+20000-U+3134F is ext-B through ext-G in one span; the unassigned gaps in it
# appear in no real text. It is not decoration: 𠮟 (U+20B9F) is on the joyo
# list, and without this a reading bracketed onto it was silently dropped —
# 𠮟【しか】る came back as 𠮟る, with no error anywhere.
BASE_CHARS = "一-鿿㐀-䶿々\U00020000-\U0003134F"

#: A base run followed by its bracketed reading. The lookahead rejects an
#: annotation with nothing in it — see :data:`_STRAY_RE`.
NOTATION_RE = re.compile(rf"([{BASE_CHARS}]+)【(?!\s*】)([^】]+)】")

#: A bracketed annotation on its own, wherever it appears. Used by :func:`strip`,
#: which historically removed brackets without caring what preceded them. The
#: class is ``*`` rather than ``+`` so an empty ``【】`` goes with the rest.
_BRACKET_RE = re.compile(r"【[^】]*】")

#: An annotation carrying no reading at all. A model emits one when it declines
#: to supply a reading, and every renderer used to pass it straight through —
#: putting literal brackets on the card and reading them aloud. That is the leak
#: this module closed for ``徐々``, so the renderers close it here too. Only
#: *empty* annotations are dropped: ``【ひと】`` with no base form in front of it
#: is left exactly where it was.
_STRAY_RE = re.compile(r"【\s*】")

_KANA_RE = re.compile(r"^[぀-ゟ゠-ヿー]+$")


class Token(NamedTuple):
    """A run of text, optionally carrying a reading.

    ``reading`` is ``None`` for plain text (kana, punctuation, latin, digits)
    and a kana string for an annotated base form.
    """

    base: str
    reading: str | None = None

    @property
    def annotated(self) -> bool:
        return self.reading is not None


def parse(text: str) -> list[Token]:
    """Split furigana notation into tokens.

    >>> parse("あの人【ひと】は")
    [Token(base='あの', reading=None), Token(base='人', reading='ひと'), Token(base='は', reading=None)]

    Malformed input degrades to plain text rather than raising: an unclosed
    bracket, an empty annotation, or a reading with no base form are all
    returned verbatim in a single unannotated token.
    """
    if not text:
        return []
    tokens: list[Token] = []
    pos = 0
    for match in NOTATION_RE.finditer(text):
        if match.start() > pos:
            tokens.append(Token(text[pos:match.start()]))
        tokens.append(Token(match.group(1), match.group(2)))
        pos = match.end()
    if pos < len(text):
        tokens.append(Token(text[pos:]))
    return tokens


def render(tokens: Iterable[Token]) -> str:
    """Write tokens back out as notation — the inverse of :func:`parse`.

    >>> render(parse("あの人【ひと】は"))
    'あの人【ひと】は'

    A token carrying an empty reading is written bare rather than as an empty
    annotation, so nothing this produces needs normalizing afterwards.

    >>> render([Token("人", ""), Token("です")])
    '人です'
    """
    return "".join(
        f"{token.base}【{token.reading}】" if token.reading else token.base
        for token in tokens
    )


def normalize(text: str) -> str:
    """Keep valid kanji readings and remove redundant kana annotations.

    Model output sometimes contains ``テスト【てすと】`` even though kana does
    not need furigana.  Such annotations are not part of the canonical format
    and would otherwise leak literal brackets from strict ruby renderers.

    >>> normalize("これはテスト【てすと】です。日本【にほん】です。")
    'これはテストです。日本【にほん】です。'
    """
    if not text:
        return ""
    return "".join(
        token.base + (f"【{token.reading}】" if token.annotated else "")
        if token.annotated
        else _BRACKET_RE.sub("", token.base)
        for token in parse(text)
    )


def to_ruby(text: str) -> str:
    """Render as ruby HTML for an Anki card.

    >>> to_ruby("人【ひと】")
    '<ruby>人<rt>ひと</rt></ruby>'

    An annotation with no reading in it is dropped rather than passed through.

    >>> to_ruby("人【】")
    '人'
    """
    return _STRAY_RE.sub("", NOTATION_RE.sub(r"<ruby>\1<rt>\2</rt></ruby>", text))


def to_mkdocs_ruby(text: str) -> str:
    """Render as mkdocs-ruby-plugin annotations for a documentation site.

    The plugin writes a reading in parentheses after its base form, and braces
    a multi-character base so the reading spans the whole run instead of
    attaching to the last character:

    >>> to_mkdocs_ruby("人【ひと】です")
    '人(ひと)です'
    >>> to_mkdocs_ruby("日本【にほん】です")
    '{日本(にほん)}です'

    An annotation with no reading in it is dropped, as everywhere else.

    >>> to_mkdocs_ruby("人【】")
    '人'

    This is a renderer, not a second notation. :mod:`jp_core.reading` emits the
    canonical bracketed form and a documentation build converts at the edge, so
    a reading that is right on a card is the same reading that reaches the site.
    """

    def render(match: re.Match) -> str:
        base, reading = match.group(1), match.group(2)
        return f"{{{base}({reading})}}" if len(base) > 1 else f"{base}({reading})"

    return _STRAY_RE.sub("", NOTATION_RE.sub(render, text))


def strip(text: str) -> str:
    """Remove the reading annotations, keeping the base forms.

    >>> strip("人【ひと】です")
    '人です'
    """
    if not text:
        return ""
    return _BRACKET_RE.sub("", text)


def to_reading(
    text: str,
    *,
    keep: Iterable[str] = (),
    clean: bool = False,
) -> str:
    """Replace annotated base forms with their readings.

    >>> to_reading("あの人【ひと】は誰【だれ】？")
    'あのひとはだれ？'

    ``keep`` names base forms that should stay as written instead of becoming
    kana. Text-to-speech engines need this: Edge TTS reads 母【はは】 correctly
    as kanji but turns the kana はは into "wawa", because it treats the leading
    は as the topic particle. A base run is kept if *any* of its characters is
    in ``keep`` — matching the original behaviour, which deliberately protected
    compounds containing a problem character.

    ``clean=True`` additionally drops punctuation and whitespace, for when the
    result is used as a sort key or a filename rather than spoken.
    """
    keep_set = set(keep)

    def render(match: re.Match) -> str:
        base, reading = match.group(1), match.group(2)
        if keep_set and any(c in keep_set for c in base):
            return base
        return reading

    out = _STRAY_RE.sub("", NOTATION_RE.sub(render, text))
    if clean:
        out = re.sub(r"[、。！？・\s/]", "", out)
    return out


def keep_base(text: str, *, overrides: Iterable[str] = ()) -> str:
    """Drop the annotations but keep the base forms — the inverse of :func:`to_reading`.

    This is the other text-to-speech strategy, and the one nihongo-it-anki
    settled on: feed the engine kanji, because a good engine gets standard
    readings right and kanji carries pitch information that bare kana loses.

    ``overrides`` names base forms the engine demonstrably misreads, which fall
    back to their kana reading. Unlike :func:`to_reading`'s ``keep``, matching
    here is on the *whole* base run, not per-character, so overriding 生 does
    not disturb 発生 or 厚生.

    >>> keep_base("昼食【ちゅうしょく】前【まえ】に")
    '昼食前に'
    >>> keep_base("提出【ていしゅつ】", overrides={"提出"})
    'ていしゅつ'
    """
    override_set = set(overrides)

    def render(match: re.Match) -> str:
        base, reading = match.group(1), match.group(2)
        return reading if base in override_set else base

    return _STRAY_RE.sub("", NOTATION_RE.sub(render, text))


def is_kana(text: str) -> bool:
    """True if ``text`` is entirely hiragana/katakana (plus the ー lengthener).

    Used to validate that a reading column really contains a reading.
    """
    return bool(text) and bool(_KANA_RE.match(text))


def annotations(text: str) -> list[tuple[str, str]]:
    """Every ``(base, reading)`` pair, for validation and vocabulary extraction."""
    return [(t.base, t.reading) for t in parse(text) if t.reading is not None]
