# JP Core browser distribution

Dependency-free ES module for static Japanese applications. It owns canonical
furigana parsing and rendering, the browser sentence record, backup schema, and
history merge rules. Browser consumers must copy this file unchanged and record
the JP Core revision in their implementation registry entry.

`replaceSentenceContent(record, {source, casual, polite}, now)` replaces text and
plain reading fields together, preserving the record identity, creation date,
review history and scheduling. Consumers must invalidate their derived content
tags when rewriting a sentence. Verify with `node --test browser/test/*.test.js`.
