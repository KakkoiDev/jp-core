# JP Core agent instructions

JP Core is the single authority for reusable Japanese content and Japanese-specific tooling.

## Boundary

JP Core owns what Japanese material is: stable IDs, text, readings, translations, register, provenance, review state, and intrinsic pronunciation or TTS exceptions.

Derived projects own how material is taught: selection, ordering, tiers, cloze targets, card types, curriculum, application UI, authentication, model providers, credentials, and infrastructure.

Do not add generic authentication, account management, API-key storage, billing, or generic LLM routing to JP Core.

## Implementation registry rule

Any KakkoiDev project that begins using JP Core must be registered in `IMPLEMENTATIONS.toml`. The integration is incomplete until its entry contains the exact GitHub URL, status, capabilities, description, relevant implementation paths, and compatible JP Core version.

When an existing consumer removes JP Core, changes its integration paths, or gains a materially new JP Core capability, update the same registry entry.

A project may use status `consumer` only after it actually depends on JP Core. Allowed statuses are `consumer`, `planned-consumer`, `candidate-consumer`, `migration-source`, `related-example`, and `retired`.

When looking for an implementation:
1. Search `IMPLEMENTATIONS.toml` by capability.
2. Prefer `consumer` as current examples.
3. Use `migration-source` only to recover behavior not yet centralized.
4. Use `related-example` for patterns, never as an implicit dependency.
5. Inspect `look_here` paths before searching an entire repository.
6. JP Core policies and tests override conflicting examples.

## Migration discipline

Migrate one capability at a time. Add or strengthen JP Core tests before switching a consumer. Preserve published Anki IDs, note GUIDs, schemas, and review history. Do not delete the consumer's old implementation until parity is proven.
