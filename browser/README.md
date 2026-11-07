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

Run the resolver again after any model-based reading correction. A model may
regress a known dictionary reading (for example 言【げん】う instead of 言【い】う).
A saved validation flag alone must not bypass this reconciliation when displaying
or correcting a sentence. Explicit learner overrides still take precedence.

Reading resolver version 2 uses longest-first dictionary matches across native
word-segmentation boundaries. Verb stems include internal kana, so compounds such
as 話し合う keep their full stem reading when conjugated. An ambiguous longer
match is reported for contextual correction; it is never discarded in favour
of shorter kanji entries. This does not make ambiguous readings context-free.

## Spaced-repetition review: `review.js`

`review.js` is the review state a sentence carries, extracted from JP Echo so
Echo and Minihongo schedule from one implementation and one state format. It is
a single file with no imports: copy it unchanged, as `jp-core.js` is copied.

It vendors [ts-fsrs](https://github.com/open-spaced-repetition/ts-fsrs) 5.4.2
(MIT, licence kept in the file): `dist/index.mjs` verbatim, minus its export
list. A test pins the hash of that section. The scheduler uses Echo's
parameters (`SCHEDULER_PARAMETERS`: retention 0.9, maximum interval 36500 days,
fuzz on, short-term on, learning steps 1m and 10m, relearning 10m). Changing the
ts-fsrs version or those parameters moves every learner's due dates, so treat
either as a breaking change. Loading the module adds `scheduler`, `diff`,
`format` and `dueFormat` to `Date.prototype`; ts-fsrs 5.4.2 does that, and so did
Echo's bundle.

**What it owns**, all as plain JSON on the sentence record:

- `srs`: a serialized ts-fsrs card (`due` and `last_review` as ISO strings or
  null, `state`, `reps`, `lapses`, `stability`, `difficulty`, `scheduled_days`,
  `elapsed_days`, `learning_steps`), plus `lastRating` and `updatedAt` written by
  each review.
- `reviewTrack`: the listening → reading → writing rotation. A pass (`"ok"`)
  moves the sentence to the next skill; any other grade keeps it there.
- Counting over the `reviews` log (`{at, rating, mode}` entries) and the
  mapping of `srs` onto Anki card columns.

| Export | Does |
| --- | --- |
| `ensureSchedule(sentence, now)` | Adds a new, immediately due card if the sentence has none |
| `isDue(sentence, now)` | True when unscheduled or `srs.due <= now` |
| `dueSentences(sentences, now)` | Due sentences, earliest due first |
| `reviewSentence(sentence, rating, now)` | `"again"` is FSRS Again, anything else (Echo sends `"ok"`) is Good |
| `REVIEW_MODES`, `ensureReviewTrack`, `reviewMode`, `nextSkill`, `recordReviewMode(sentence, rating, at)`, `skillMix` | The skill rotation |
| `reviewStats(sentences, now)` | 24-hour, 7-day and per-mode counts from `reviews` |
| `ankiSchedule(srs, createdSeconds)` | Anki `type`, `queue`, `due`, `interval`, `factor`, `reps`, `lapses`, `left`, or null for an unreviewed card |
| `TS_FSRS_VERSION`, `SCHEDULER_PARAMETERS` | The pinned scheduler |

All functions return new objects and never mutate their input.

**What consumers own:** which sentences enter a session and how many (daily
limits, new versus review caps), the review UI and every word on it (mode
labels, glyphs, reason lines, availability messages), appending entries to
`reviews`, undo, and persistence. Echo's `sessionLimit`, `limitReviewSession`,
`REVIEW_MODE_META`, `skillReason`, `dueLine` and `reviewAvailabilityMessage`
stay in Echo for that reason.

`browser/test/review.test.js` replays long review histories through this module
and through a byte-for-byte copy of Echo's `srs.js`
(`browser/test/fixtures/echo-srs.js`, Echo a32e9dd) and requires identical
records at every step, so progress Echo has already scheduled continues exactly
as before.
