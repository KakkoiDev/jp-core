# Migration plan

## Goal

Make JP Core the single authority for reusable Japanese data and tooling while derived projects retain their collections, pedagogy, UI, authentication, providers, and infrastructure.

## Sequence

1. Establish JP Core from the current jpanki codebase.
2. Keep the existing `jpanki` Python import temporarily for compatibility.
3. Migrate `KakkoiDev/jpanki` to depend on JP Core and become a thin compatibility package.
4. Extract mature, tested capabilities from migration-source repositories into JP Core.
5. Migrate consumers one project and one capability at a time.
6. Mark registry entries `consumer` only after their dependency and integration are real.
7. Remove duplicated implementations only after parity tests pass.

## First migrations

1. `https://github.com/KakkoiDev/jpanki` — compatibility consumer.
2. `https://github.com/KakkoiDev/bible-japanese-anki` — small end-to-end deck consumer.
3. `https://github.com/KakkoiDev/nihongo-it-anki` — mature Anki, TTS, pronunciation, and audit pipeline.
4. `https://github.com/KakkoiDev/anki-voiced` — consolidate the generic CLI.
5. `https://github.com/KakkoiDev/minihongo` — corpus, chat integration, and speech use.

## Compatibility rule

A migration must preserve externally meaningful behavior unless a separately reviewed change explicitly replaces it. This includes stable deck/model IDs, note GUIDs, card fields, audio references, and released import behavior.
