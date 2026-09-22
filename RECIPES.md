# JP Core recipes

These examples use public APIs. Applications should not copy their
implementations.

## Corpus and collection

    from jp_core.corpus import Collection, CollectionItem, Corpus, Sentence, sentence_id

    sentence = Sentence(
        id=sentence_id("my-corpus", "lesson-1/example-1"),
        japanese="日本語【にほんご】を勉強【べんきょう】します。",
        translation="I study Japanese.",
    )
    corpus = Corpus([sentence])
    lesson = Collection(
        id="lesson-1",
        title="First lesson",
        items=[CollectionItem(sentence.id, order=1, prompt="Read aloud")],
    )
    resolved = lesson.resolve(corpus)

Collections store only sentence IDs and teaching metadata. They do not copy
Japanese sentences or translations.

## Guardrails

    from jp_core.guardrails import Policy, max_length, require_furigana_for_kanji, require_japanese

    policy = Policy("beginner", [
        require_japanese,
        max_length(40),
        require_furigana_for_kanji,
    ])
    diagnostics = policy.check("日本語【にほんご】です。")

Use policy.require(text) at a fail-closed build boundary.

## TTS provider integration

    from jp_core.speech import ProviderRegistry, SynthesisRequest, Voice

    providers = ProviderRegistry()
    providers.register_tts("application-provider", my_provider)
    request = SynthesisRequest(
        text="提出【ていしゅつ】します。",
        voice=Voice("ja-JP-NanamiNeural"),
        output=audio_path,
        pronunciation_overrides={"提出": "ていしゅつ"},
    )
    await providers.tts("application-provider").synthesize(request)

Applications resolve credentials and construct providers. JP Core never stores
API keys.

## Ruby HTML and toggle

    from jp_core.web import FURIGANA_CSS, FURIGANA_TOGGLE_JS, ruby_html, toggle_button

    body = ruby_html("日本語【にほんご】")
    control = toggle_button(label="ふりがな")

Include the CSS once and load the JavaScript after the page body.

## Agent discovery

    from jp_core.agent import find_examples

    examples = find_examples("anki-deck-generation", consumers_only=True)

When a new project adopts JP Core, update IMPLEMENTATIONS.toml in the same
change or immediately afterward. Record its exact URL, integration paths,
pinned JP Core revision, and verified project revision.

## Generate furigana for a sentence

    from jp_core import furigana, reading

    annotated = reading.annotate("受け付けは一階にあります。")
    # '受【う】け付【つ】けは一階【いっかい】にあります。'

    furigana.to_ruby(annotated)         # for a card
    furigana.to_mkdocs_ruby(annotated)  # for a documentation site
    furigana.strip(annotated)           # back to plain text

Needs `jp-core[morphology]`. Readings already in the text are kept, so a
correction by hand survives the next build, and a compound the analyser splits
is repaired from `reading.PRONUNCIATION_OVERRIDES` — extend it per call with
`reading.annotate(text, overrides={...})`.

In a browser, `browser/jp-core.js` carries the same alignment and the same
override table; supply the token stream from an analyser of your own and call
`readingsToNotation`.
