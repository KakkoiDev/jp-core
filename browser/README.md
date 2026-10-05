# JP Core browser distribution

Dependency-free ES module for static Japanese applications. It owns canonical
furigana parsing and rendering, the browser sentence record, backup schema, and
history merge rules. Browser consumers must copy this file unchanged and record
the JP Core revision in their implementation registry entry.

`replaceSentenceContent(record, {source, casual, polite}, now)` replaces text and
plain reading fields together, preserving the record identity, creation date,
review history and scheduling. Consumers must invalidate their derived content
tags when rewriting a sentence. Verify with `node --test browser/test/*.test.js`.

`japanese-words.js` exports `createJapaneseWordMatcher(dictionary)` for lexical
coverage and clickable surface spans. Dictionary records provide `id`, `w`,
`r`, `k` (optional), and `pos`. Spans include alternative dictionary IDs for
ambiguous readings. Unmatched katakana runs are returned whole with a null ID;
consumers must display an unknown-word state rather than substring definitions.

`grammar-spans.js` validates grammar analysis against known point IDs and exact
quoted sentence text, including occurrence indices for repeated particles.
Consumers own grammar catalogues, AI providers and teaching UI.

`sentenceIdentity(record)` keys a sentence by its language pair and normalized target text, ignoring furigana and Japanese layout whitespace. `mergeSentences(current, incoming)` preserves existing content-duplicate card IDs and scheduling, appends new sentences, unions grammar/vocabulary links, and avoids replacing reviewed scheduling with an unreviewed backup. Untagged sentences remain untagged.

`japanese-readings.js` provides `createReadingResolver(dictionary)` using native
Japanese `Intl.Segmenter`, dictionary readings and kanji/kana alignment. Unknown
or ambiguous entries are returned in `issues` for contextual checking; explicit
learner overrides take precedence. `readingText(notation)` feeds the displayed
reading to speech. `validateReadingCorrection` rejects changed surface text,
missing annotations and non-kana readings. Consumers own model requests,
backfill scheduling, credentials and persistence.
