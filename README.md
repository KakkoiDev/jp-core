# JP Core

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

