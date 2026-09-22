"""Reading generation: alignment, overrides, and the analyser adapters.

The alignment is the part worth testing hard, and it takes a token stream, so
almost everything here runs on a stub tokenizer with no dictionary in sight.
The two real analysers are exercised separately and skipped when their extra is
not installed.
"""
import pytest

from jp_core import furigana, reading

# (surface, analyser reading, expected notation). Every one of these is a shape
# the aligner has to get right: okurigana at the end, in the middle, and both
# ends at once; a reading that covers the whole token; a kana prefix that is
# part of the word.
PAIRS = [
    ("食べる", "タベル", "食【た】べる"),
    ("話し合う", "ハナシアウ", "話【はな】し合【あ】う"),
    ("見上げる", "ミアゲル", "見上【みあ】げる"),
    ("取り引き", "トリヒキ", "取【と】り引【ひ】き"),
    ("申し込み", "モウシコミ", "申【もう】し込【こ】み"),
    ("受け付け", "ウケツケ", "受【う】け付【つ】け"),
    ("食べ物", "タベモノ", "食【た】べ物【もの】"),
    ("今日", "キョウ", "今日【きょう】"),
    ("大人", "オトナ", "大人【おとな】"),
    ("一日", "ツイタチ", "一日【ついたち】"),
    ("日本語", "ニホンゴ", "日本語【にほんご】"),
    ("日々", "ヒビ", "日々【ひび】"),
    ("お茶", "オチャ", "お茶【ちゃ】"),
    ("行きます", "イキマス", "行【い】きます"),
    ("新しい", "アタラシイ", "新【あたら】しい"),
    ("静かだ", "シズカダ", "静【しず】かだ"),
]


@pytest.mark.parametrize("surface,analyser,expected", PAIRS)
def test_places_the_reading_on_the_kanji_runs(surface, analyser, expected):
    assert reading.from_tokens([(surface, analyser)]) == expected


@pytest.mark.parametrize("surface,analyser,expected", PAIRS)
def test_what_it_emits_parses_back_to_what_it_meant(surface, analyser, expected):
    """furigana.py must recognise every run reading.py brackets. If the two
    character classes drift, the reading is dropped as a stray and nothing
    anywhere raises — the kana simply stop appearing on the card."""
    emitted = reading.from_tokens([(surface, analyser)])
    assert furigana.normalize(emitted) == emitted
    assert furigana.strip(emitted) == surface
    assert furigana.annotations(emitted), f"{surface} produced no annotation"


def test_kana_only_and_reading_less_tokens_pass_through():
    assert reading.from_tokens([("テスト", "テスト")]) == "テスト"
    assert reading.from_tokens([("やる", "ヤル")]) == "やる"
    assert reading.from_tokens([("謎", "")]) == "謎"
    assert reading.from_tokens([("謎", "*")]) == "謎"


@pytest.mark.parametrize("surface,bad", [
    ("食べる", "のむ"),        # the okurigana does not match
    ("お茶", "ちゃ"),          # the leading kana is missing from the reading
    ("見る", "みる "),         # trailing whitespace is not part of a reading
    ("駅", "えき です"),       # nor is an explanation
    ("駅", "eki"),            # nor romaji
])
def test_refuses_to_guess(surface, bad):
    """A wrong reading is worse than none: it is plausible, it is memorised,
    and in a shadowing app it is said out loud."""
    assert reading.align(surface, bad) is None
    assert reading.from_tokens([(surface, bad)]) == surface


def test_overrides_repair_a_compound_the_analyser_split():
    """一階 is いっかい, but every analyser that segments it loses the gemination,
    because the sound change only exists across the seam."""
    split = [("一", "イチ"), ("階", "カイ")]
    assert reading.from_tokens(split) == "一階【いっかい】"
    assert reading.from_tokens([("六", "ロク"), ("本", "ホン")]) == "六本【ろっぽん】"
    assert reading.from_tokens([("日本", "ニッポン")]) == "日本【にほん】"


def test_overrides_prefer_the_longest_match():
    tokens = [("一", "イチ"), ("週間", "シュウカン")]
    assert reading.from_tokens(tokens) == "一週間【いっしゅうかん】"


def test_caller_overrides_win_over_the_builtin_table():
    assert reading.from_tokens(
        [("日本", "ニッポン")], overrides={"日本": "にっぽん"}
    ) == "日本【にっぽん】"


def test_an_override_does_not_fire_inside_a_larger_token():
    """八百屋 is やおや, not はっぴゃく屋. Overrides match whole tokens, so an
    analyser that keeps the compound together is never second-guessed."""
    assert reading.from_tokens([("八百屋", "ヤオヤ")]) == "八百屋【やおや】"


def test_ambiguous_compounds_are_left_split_on_purpose():
    """十分 is じゅっぷん as a duration and じゅうぶん as 'enough'. Nothing in a
    token stream distinguishes them, so it stays out of the table."""
    assert "十分" not in reading.PRONUNCIATION_OVERRIDES
    assert reading.from_tokens([("十", "ジュウ"), ("分", "フン")]) == "十【じゅう】分【ふん】"


def test_annotate_preserves_readings_already_present():
    """Annotating twice is annotating once, so a hand-corrected reading
    survives the next build."""
    stub = lambda text: [(text, "ゴ")]
    assert reading.annotate("日本【にっぽん】語", tokenize=stub) == "日本【にっぽん】語【ご】"


def test_annotate_is_empty_for_empty():
    assert reading.annotate("", tokenize=lambda text: []) == ""


def test_is_hiragana():
    assert reading.is_hiragana("き")
    assert not reading.is_hiragana("木")
    assert not reading.is_hiragana("")


def test_to_hiragana_leaves_the_counter_marks_alone():
    """ヶ and ヵ have no hiragana anyone writes; converting them turns 一ヶ月
    into 一ゖ月."""
    assert reading.to_hiragana("ニホン") == "にほん"
    assert reading.to_hiragana("一ヶ月") == "一ヶ月"


def test_mecab_tokenizer_reads_a_sentence():
    pytest.importorskip("fugashi")
    pytest.importorskip("ipadic")
    annotated = reading.annotate("受け付けは一階にあります。", tokenize=reading.mecab_tokenizer())
    assert annotated == "受【う】け付【つ】けは一階【いっかい】にあります。"


def test_kakasi_tokenizer_declines_a_bare_kun_reading():
    """pykakasi sees a kanji run with no context, so 生まれる and 生きる are
    indistinguishable to it. It yields no reading rather than picking one."""
    pytest.importorskip("pykakasi")
    tokenize = reading.kakasi_tokenizer()
    assert reading.annotate("生まれる", tokenize=tokenize) == "生まれる"
    assert reading.annotate("日本語", tokenize=tokenize) == "日本語【にほんご】"


def test_default_tokenizer_explains_itself_when_nothing_is_installed(monkeypatch):
    def refuse():
        raise ImportError("no analyser")

    monkeypatch.setattr(reading, "mecab_tokenizer", refuse)
    monkeypatch.setattr(reading, "kakasi_tokenizer", refuse)
    with pytest.raises(RuntimeError, match=r"jp-core\[morphology\]"):
        reading.default_tokenizer()
