"""Deterministic Japanese reading generation.

This module owns Japanese-aware token recognition and reading generation.
Consumers remain responsible for their document format and teaching choices.

A reading is a dictionary lookup, not a generation task. Asking a language
model for one is the single most reliable way to get a wrong one, and a wrong
reading is worse than none at all: it is silently plausible, it is what a
learner memorises, and in a shadowing app it is what they say out loud. So the
readings here come from a morphological analyser, and anything that does not
line up is left bare rather than guessed at.

Output is the canonical ``漢字【かんじ】`` notation that :mod:`jp_core.furigana`
parses. Rendering it as ruby, as mkdocs-ruby parentheses, or as bare kana is
that module's job — this one decides what the reading *is*, exactly once.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Iterator, Mapping

from . import furigana

#: Runs this module will annotate, kept identical to the class
#: :data:`jp_core.furigana.NOTATION_RE` accepts. If the two ever drift, a run
#: we bracket is one the parser does not recognise, and every renderer drops
#: the reading as a stray with no error anywhere.
KANJI_RE = re.compile(rf"[{furigana.BASE_CHARS}]+")

_KANA_RE = re.compile(r"^[ぁ-ゟー]+$")

#: Compounds an analyser gets wrong because it segments them, and segmenting
#: loses the sound change that only exists across the seam. IPADIC reads 一階
#: as いち + かい, and no amount of context will fix that: the gemination is a
#: property of the compound, which is to say it is intrinsic pronunciation, and
#: therefore ours.
#:
#: Deliberately not exhaustive, and deliberately free of ambiguity. 十分 is
#: absent because it is じゅっぷん as a duration and じゅうぶん as "enough", and
#: this table has no way to tell them apart; guessing would trade a reading
#: that is visibly split for one that is confidently wrong. Consumers extend it
#: through ``overrides``.
#:
#: 一ヶ月 is absent for a different reason: ヶ is not in
#: :data:`jp_core.furigana.BASE_CHARS`, so 一ヶ月【いっかげつ】 does not parse
#: and the reading would be dropped as a stray on the way to the page. The
#: argument for admitting it is the one already made there for 々 — it is part
#: of the written base form without being an ideograph — but that class was
#: verified against the minihongo and nihongo-it corpora, so widening it is a
#: change to make there, with those corpora in front of you, not here.
PRONUNCIATION_OVERRIDES: Mapping[str, str] = {
    # 一 before k/s/t/h — the most common gemination in the language.
    "一回": "いっかい", "一階": "いっかい", "一個": "いっこ", "一冊": "いっさつ",
    "一歳": "いっさい", "一足": "いっそく", "一点": "いってん", "一杯": "いっぱい",
    "一匹": "いっぴき", "一分": "いっぷん", "一本": "いっぽん", "一泊": "いっぱく",
    "一枚": "いちまい", "一週間": "いっしゅうかん", "一生": "いっしょう",
    "一緒": "いっしょ",
    # 六 and 八 before h/k.
    "六回": "ろっかい", "六階": "ろっかい", "六個": "ろっこ", "六本": "ろっぽん",
    "六匹": "ろっぴき", "六杯": "ろっぱい", "六分": "ろっぷん",
    "八回": "はっかい", "八階": "はっかい", "八個": "はっこ", "八本": "はっぽん",
    "八匹": "はっぴき", "八杯": "はっぱい", "八分": "はっぷん", "八冊": "はっさつ",
    # 十 — じゅっ is the spoken form; じっ is the older prescriptive one.
    "十回": "じゅっかい", "十階": "じゅっかい", "十個": "じゅっこ", "十本": "じゅっぽん",
    "十匹": "じゅっぴき", "十杯": "じゅっぱい", "十冊": "じゅっさつ", "十歳": "じゅっさい",
    # 三 and 何 take rendaku rather than gemination.
    "三本": "さんぼん", "三匹": "さんびき", "三杯": "さんばい", "三階": "さんがい",
    "三分": "さんぷん", "三百": "さんびゃく", "三千": "さんぜん",
    "何本": "なんぼん", "何匹": "なんびき", "何杯": "なんばい", "何階": "なんがい",
    "何分": "なんぷん", "何回": "なんかい",
    # IPADIC's headword reading, which is not the one anyone says.
    "日本": "にほん",
}

#: A token stream: ``(surface, reading)`` pairs, the reading in kana or empty
#: when the analyser has none. Both bundled analysers are adapted to this, so
#: the alignment below is testable without a dictionary anywhere near it.
Tokenizer = Callable[[str], Iterable[tuple[str, str]]]


def is_hiragana(char: str) -> bool:
    """Return whether *char* is a hiragana code point."""
    return bool(char) and "぀" <= char <= "ゟ"


def to_hiragana(text: str) -> str:
    """Convert katakana to hiragana, which is how a reading is written.

    ァ..ヴ only. ヵ and ヶ sit at the top of the katakana block but have no
    hiragana anyone writes, and 一ヶ月 would come back as 一ゖ月.

    >>> to_hiragana("ニホンゴ")
    'にほんご'
    """
    return "".join(
        chr(ord(c) - 0x60) if "ァ" <= c <= "ヴ" else c for c in text
    )


def align(base: str, reading: str) -> list[furigana.Token] | None:
    """Place *reading* on the kanji runs inside *base*.

    An analyser gives a reading for a whole token, but the notation annotates
    the kanji runs inside it, so the kana in the surface have to be found in
    the reading first. 話し合う / はなしあう pins し at index 2 and う at 4,
    which leaves はな for 話 and あ for 合:

    >>> align("話し合う", "はなしあう")
    [Token(base='話', reading='はな'), Token(base='し', reading=None), Token(base='合', reading='あ'), Token(base='う', reading=None)]

    Returns ``None`` when the two do not line up, rather than splitting the
    difference — the caller then emits the token bare.

    >>> align("食べる", "のむ") is None
    True

    A reading that is not kana is refused outright. Anything else, and a base
    with no okurigana to pin would swallow it whole.

    >>> align("駅", "えき です") is None
    True
    """
    if not base or not reading or not _KANA_RE.match(reading):
        return None
    runs: list[list] = []
    for char in base:
        kanji = bool(KANJI_RE.match(char))
        if runs and runs[-1][0] == kanji:
            runs[-1][1] += char
        else:
            runs.append([kanji, char])
    if not any(kanji for kanji, _ in runs):
        return [furigana.Token(base)]
    tokens: list[furigana.Token] = []
    pos = 0
    for index, (kanji, text) in enumerate(runs):
        if not kanji:
            if not reading.startswith(text, pos):
                return None
            tokens.append(furigana.Token(text))
            pos += len(text)
            continue
        following = runs[index + 1] if index + 1 < len(runs) else None
        # Every kanji run needs at least one kana of its own, hence pos + 1.
        end = reading.find(following[1], pos + 1) if following else len(reading)
        if end < 0 or end <= pos:
            return None
        tokens.append(furigana.Token(text, reading[pos:end]))
        pos = end
    return tokens if pos == len(reading) else None


def _apply_overrides(
    tokens: list[tuple[str, str]], overrides: Mapping[str, str]
) -> Iterator[tuple[str, str]]:
    """Merge adjacent tokens whose joined surface has a known reading."""
    if not overrides:
        yield from tokens
        return
    longest = max(len(key) for key in overrides)
    index = 0
    while index < len(tokens):
        joined = ""
        match: tuple[int, str, str] | None = None
        for span in range(index, len(tokens)):
            joined += tokens[span][0]
            if len(joined) > longest:
                break
            if joined in overrides:
                match = (span, joined, overrides[joined])
        if match:
            span, surface, reading = match
            yield surface, reading
            index = span + 1
        else:
            yield tokens[index]
            index += 1


def from_tokens(
    tokens: Iterable[tuple[str, str]],
    *,
    overrides: Mapping[str, str] | None = None,
) -> str:
    """Render a ``(surface, reading)`` stream as canonical notation.

    >>> from_tokens([("駅", "エキ"), ("は", "ハ"), ("どこ", "ドコ")])
    '駅【えき】はどこ'

    Overrides are matched against runs of adjacent tokens, which is what makes
    them able to repair a compound the analyser split:

    >>> from_tokens([("一", "イチ"), ("階", "カイ")], overrides={"一階": "いっかい"})
    '一階【いっかい】'
    """
    merged = _apply_overrides(list(tokens), {**PRONUNCIATION_OVERRIDES, **(overrides or {})})
    out = []
    for surface, reading in merged:
        kana = to_hiragana(reading) if reading and reading != "*" else ""
        placed = align(surface, kana) if kana else None
        out.append(furigana.render(placed) if placed else surface)
    return "".join(out)


def mecab_tokenizer() -> Tokenizer:
    """A tokenizer backed by MeCab and IPADIC, via ``jp-core[morphology]``.

    IPADIC rather than UniDic, which the verification path uses: UniDic splits
    by short unit word, so 日本語 arrives as 日本 + 語 and 金曜日 as 金曜 + 日.
    That is the right call for checking a reading morpheme by morpheme and the
    wrong one for writing furigana, where the compound's own reading is the
    answer. Measured over a 30-sentence corpus, UniDic split five compounds
    IPADIC kept whole and read 私 as わたくし.
    """
    import fugashi
    import ipadic

    tagger = fugashi.GenericTagger(ipadic.MECAB_ARGS)

    def tokenize(text: str) -> Iterator[tuple[str, str]]:
        for word in tagger(text):
            feature = word.feature
            reading = feature[7] if len(feature) > 7 else "*"
            yield word.surface, "" if reading == "*" else reading

    return tokenize


def kakasi_tokenizer() -> Tokenizer:
    """A tokenizer backed by pykakasi, via ``jp-core[generation]``.

    The degraded path, kept because it needs no dictionary. pykakasi reads a
    kanji run in isolation, so a single kanji followed by okurigana is yielded
    without a reading: 生まれる and 生きる differ only in the okurigana, and an
    isolated lookup cannot see it. Prefer :func:`mecab_tokenizer`.
    """
    import pykakasi

    converter = pykakasi.kakasi()

    def tokenize(text: str) -> Iterator[tuple[str, str]]:
        pos = 0
        for match in KANJI_RE.finditer(text):
            if match.start() > pos:
                yield text[pos:match.start()], ""
            run = match.group(0)
            if len(run) == 1 and is_hiragana(text[match.end():match.end() + 1]):
                yield run, ""
            else:
                reading = "".join(part["hira"] for part in converter.convert(run))
                yield run, "" if not reading or reading == run else reading
            pos = match.end()
        if pos < len(text):
            yield text[pos:], ""

    return tokenize


def default_tokenizer() -> Tokenizer:
    """The best analyser installed, MeCab first."""
    try:
        return mecab_tokenizer()
    except ImportError:
        pass
    try:
        return kakasi_tokenizer()
    except ImportError as exc:
        raise RuntimeError(
            "Reading generation requires the jp-core[morphology] extra "
            "(MeCab and IPADIC) or, for the degraded path, jp-core[generation]"
        ) from exc


def annotate(
    text: str,
    *,
    overrides: Mapping[str, str] | None = None,
    tokenize: Tokenizer | None = None,
) -> str:
    """Annotate the bare kanji runs in *text* with their readings.

    Readings already present are preserved exactly, so annotating twice is
    the same as annotating once, and a reading corrected by hand survives the
    next build:

    >>> annotate("日本【にっぽん】語", tokenize=lambda t: [("語", "ゴ")])
    '日本【にっぽん】語【ご】'

    *tokenize* defaults to :func:`default_tokenizer`, which needs one of the
    optional analyser extras installed.
    """
    if not text:
        return ""
    if tokenize is None:
        tokenize = default_tokenizer()
    return "".join(
        (token.base + f"【{token.reading}】")
        if token.annotated
        else from_tokens(tokenize(token.base), overrides=overrides)
        for token in furigana.parse(text)
    )
