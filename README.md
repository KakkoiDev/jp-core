# JP Core

JP Core is the canonical library for Japanese content and Japanese-specific
tooling across KakkoiDev projects. It deliberately does not own authentication,
general chat state, provider billing, or application navigation.

## Shared APIs

| API | Owns |
| --- | --- |
| jp_core.text | Unicode normalization, Japanese script detection, sentence splitting |
| jp_core.furigana / reading | Canonical annotations, renderers, deterministic reading generation |
| jp_core.corpus | Sentences, provenance, stable IDs, queries, and teaching collections |
| jp_core.speech | TTS/STT contracts, requests, transcripts, comparison, provider registry |
| jp_core.anki | Stable deck, note, media, ID, validation, and packaging facade |
| jp_core.web | Safe ruby HTML plus framework-neutral furigana toggle assets |
| jp_core.guardrails | Composable policies returning structured diagnostics |
| jp_core.pipeline | Deterministic steps and reproducibility manifests |
| jp_core.agent | Capability discovery and concrete implementation routing |

The corpus owns what a sentence is. A collection owns how it is taught.

Optional integrations are installed with jp-core[tts],
jp-core[generation], jp-core[morphology], or jp-core[all]. Existing
jp-core[audio] installations remain supported as an alias for the TTS extra.

See [RECIPES.md](RECIPES.md) for minimal integrations.

The canonical library of reusable Japanese content and Japanese-specific tooling for KakkoiDev projects.

JP Core owns **what Japanese material is**: stable identity, text, readings, translations, register, provenance, review state, furigana, pronunciation, Japanese speech preparation, validation, and reusable generation mechanics.

Derived projects own **how that material is taught or presented**: collections, ordering, tiers, cloze targets, cards, curriculum, user interfaces, authentication, model providers, credentials, and infrastructure.

## Current state

JP Core began as a copy of [KakkoiDev/jpanki](https://github.com/KakkoiDev/jpanki). Its Python import namespace is `jp_core`; the original `jpanki` project is retained as a compatibility package that re-exports this API.

- [Migration plan](MIGRATION.md)
- [Implementation and example registry](IMPLEMENTATIONS.toml)
- [Agent and ownership rules](AGENTS.md)

A KakkoiDev project using JP Core must be registered in `IMPLEMENTATIONS.toml`. Adding the dependency without updating that registry is an incomplete integration.

## Scope boundary

JP Core does not own authentication, user accounts, API-key storage, billing, generic LLM provider routing, conversation persistence, application UI, or deployment infrastructure. It provides Japanese-specific content and transformations that those applications consume.

## What's here

| Module | Owns |
|---|---|
| `furigana` | The `漢字【かな】` notation — one parser, several renderers |
| `romaji` | kana → rōmaji, for filenames and reading cross-checks |
| `theme` | The card CSS design system, as composable layers |
| `model` | genanki model/deck/package construction, media refs |
| `ids` | The deck/model ID registry that keeps consumers from colliding |
| `tts` | Edge TTS primitives: synthesise, normalise, merge |
| `validate` | CSV schema checks and build-freshness manifests |
| `release` | Publishing `.apkg` files as GitHub release assets |

## Install

```bash
uv add jp-core --git https://github.com/KakkoiDev/jp-core
```

Audio generation needs the extra and `ffmpeg` on `PATH`:

```bash
uv add "jp-core[audio]" --git https://github.com/KakkoiDev/jp-core
```

## The two rules that matter

**Note GUIDs are derived from a stable business key, never from content.**
`genanki`'s default hashes every field, so correcting one typo in a gloss
creates a *new* note and silently resets that card's review history for
everyone who re-imports the deck. Pass a key that identifies the note
independently of what it says:

```python
guid = jp_core.note_guid("bible", lesson, japanese)   # not the English gloss
```

**Deck and model IDs are registered, not invented.** An ID collision between
two decks silently merges them inside a user's collection. `ids.toml` records
every ID already published; `assert_unique()` fails the build on a clash. IDs
in that file are historical fact — record them, never renumber them.

## Development

```bash
uv sync
uv run pytest
```

The furigana tests are golden-file tests captured from the two original
implementations. They exist so that extraction cannot silently change how
hundreds of already-published cards render. Treat a diff there as a bug in the
library, not a stale fixture.
