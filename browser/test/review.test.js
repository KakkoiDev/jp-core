import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import {
  REVIEW_MODES, SCHEDULER_PARAMETERS, TS_FSRS_VERSION, ankiSchedule, dueSentences, ensureReviewTrack,
  ensureSchedule, isDue, nextSkill, recordReviewMode, reviewMode, reviewSentence, reviewStats, skillMix,
} from "../review.js";
// JP Echo's srs.js at a32e9dd (last changed in b84fec8), copied byte for byte.
// It is the behaviour this module must keep: learners already have progress
// scheduled by it.
import * as echo from "./fixtures/echo-srs.js";

const now = new Date("2026-01-01T12:00:00Z");
const sentence = { id: "one", english: "Hello", japanese: "こんにちは", createdAt: now.toISOString(), updatedAt: now.toISOString() };

// ---- Vendored ts-fsrs -----------------------------------------------------------

test("the vendored ts-fsrs section is npm ts-fsrs@5.4.2 dist/index.mjs, unedited", () => {
  const source = readFileSync(new URL("../review.js", import.meta.url), "utf8");
  const start = source.indexOf("// SOFTWARE.\n") + "// SOFTWARE.\n".length;
  const end = source.indexOf("// ---- END vendored ts-fsrs");
  assert.ok(start > 0 && end > start);
  // sha256 of dist/index.mjs without its last two lines (export list, source map).
  const hash = createHash("sha256").update(source.slice(start, end)).digest("hex");
  assert.equal(hash, "1aeeb9b60379a278a285c14bd2aac8aca5814239df569aa4275fe5b85e801c8e");
  assert.match(source.slice(start, end), /const version="5\.4\.2";/);
  assert.equal(TS_FSRS_VERSION, "5.4.2");
});

test("the module has no imports, so a consumer can copy it alone", () => {
  const source = readFileSync(new URL("../review.js", import.meta.url), "utf8");
  assert.doesNotMatch(source, /^\s*import\s/m);
});

test("scheduler parameters are Echo's", () => {
  assert.deepEqual(JSON.parse(JSON.stringify(SCHEDULER_PARAMETERS)), {
    request_retention: 0.9, maximum_interval: 36500, enable_fuzz: true, enable_short_term: true,
    learning_steps: ["1m", "10m"], relearning_steps: ["10m"],
  });
  assert.ok(Object.isFrozen(SCHEDULER_PARAMETERS));
});

// ---- Scheduling (ported from Echo's test/srs.test.js) ------------------------------

test("new translations are immediately due", () => {
  const scheduled = ensureSchedule(sentence, now);
  assert.equal(isDue(scheduled, now), true);
  assert.deepEqual(dueSentences([scheduled], now).map(item => item.id), ["one"]);
});

test("OK and Again use FSRS ratings", () => {
  const ok = reviewSentence(sentence, "ok", now);
  const again = reviewSentence(sentence, "again", now);
  assert.equal(ok.srs.reps, 1);
  assert.equal(again.srs.reps, 1);
  assert.equal(again.srs.lapses, 0);
  assert.ok(Date.parse(ok.srs.due) > now.getTime());
  assert.ok(Date.parse(again.srs.due) > now.getTime());
});

test("a scheduled sentence is returned unchanged by ensureSchedule", () => {
  const scheduled = ensureSchedule(sentence, now);
  assert.equal(ensureSchedule(scheduled, new Date("2027-01-01T00:00:00Z")), scheduled);
});

test("the stored card is plain JSON with ISO dates", () => {
  const reviewed = reviewSentence(sentence, "ok", now);
  assert.deepEqual(JSON.parse(JSON.stringify(reviewed)), reviewed);
  assert.equal(reviewed.srs.last_review, now.toISOString());
  assert.equal(ensureSchedule(sentence, now).srs.last_review, null);
  assert.equal(reviewed.lastRating, "ok");
  assert.equal(reviewed.updatedAt, now.toISOString());
});

test("due sentences sort by due date, unscheduled ones by creation", () => {
  const later = { id: "later", createdAt: "2025-12-31T00:00:00Z" };
  const early = { id: "early", createdAt: "2025-12-01T00:00:00Z" };
  const reviewed = reviewSentence({ id: "future", createdAt: "2025-01-01T00:00:00Z" }, "ok", now);
  assert.deepEqual(dueSentences([later, reviewed, early], now).map(item => item.id), ["early", "later"]);
});

// ---- Parity with Echo's current srs.js --------------------------------------------

// A deterministic stream of numbers in [0, 1).
function lcg(seed) {
  let state = seed >>> 0;
  return () => (state = (Math.imul(state, 1664525) + 1013904223) >>> 0) / 2 ** 32;
}

test("a card Echo has already scheduled gets the same next state", () => {
  // Progress as Echo stores it, after a few reviews.
  let stored = echo.reviewSentence(sentence, "ok", now);
  stored = echo.reviewSentence(stored, "ok", new Date(Date.parse(stored.srs.due)));
  stored = echo.reviewSentence(stored, "again", new Date(Date.parse(stored.srs.due) + 3600000));
  stored = JSON.parse(JSON.stringify(stored));
  for (const rating of ["ok", "again"]) {
    const at = new Date(Date.parse(stored.srs.due) + 5 * 60000);
    assert.deepEqual(reviewSentence(stored, rating, at), echo.reviewSentence(stored, rating, at));
  }
});

test("long review histories schedule identically to Echo", () => {
  const random = lcg(20261107);
  for (let card = 0; card < 40; card += 1) {
    const created = new Date(Date.UTC(2026, 0, 1) + Math.floor(random() * 365) * 86400000);
    let ours = { id: `s${card}`, createdAt: created.toISOString() };
    let theirs = ours;
    let at = created;
    for (let step = 0; step < 25; step += 1) {
      const rating = random() < 0.25 ? "again" : "ok";
      // Sometimes on time, sometimes early, sometimes weeks late.
      const due = Date.parse(theirs.srs?.due || at.toISOString());
      const offset = (random() - 0.2) * 20 * 86400000 * random();
      at = new Date(Math.max(at.getTime() + 60000, due + offset));
      ours = reviewSentence(JSON.parse(JSON.stringify(ours)), rating, at);
      theirs = echo.reviewSentence(JSON.parse(JSON.stringify(theirs)), rating, at);
      assert.deepEqual(ours, theirs, `card ${card}, review ${step}`);
      assert.equal(isDue(ours, at), echo.isDue(theirs, at));
    }
  }
});

test("ensureSchedule, isDue and dueSentences match Echo", () => {
  const items = [
    { id: "a", createdAt: "2026-01-02T00:00:00Z" },
    reviewSentence({ id: "b", createdAt: "2025-12-01T00:00:00Z" }, "again", new Date("2025-12-31T23:00:00Z")),
    reviewSentence({ id: "c", createdAt: "2025-11-01T00:00:00Z" }, "ok", now),
    { id: "d", createdAt: "2025-10-01T00:00:00Z" },
  ];
  assert.deepEqual(ensureSchedule(items[0], now), echo.ensureSchedule(items[0], now));
  for (const item of items) assert.equal(isDue(item, now), echo.isDue(item, now));
  assert.deepEqual(dueSentences(items, now), echo.dueSentences(items, now));
});

// ---- Review modes (ported from Echo's test/review-modes.test.js) -------------------

test("legacy sentences start with Listening and zero progress", () => {
  const tracked = ensureReviewTrack({ id: "s1" });
  assert.equal(reviewMode(tracked), "listening");
  assert.deepEqual(tracked.reviewTrack.completed, { listening: 0, reading: 0, writing: 0 });
  assert.deepEqual(tracked.reviewTrack.attempts, { listening: 0, reading: 0, writing: 0 });
  assert.deepEqual(REVIEW_MODES, ["listening", "reading", "writing"]);
});

test("OK rotates one skill at a time and records independent completion", () => {
  const at = new Date("2026-10-01T12:00:00Z");
  const a = recordReviewMode({ id: "s1" }, "ok", at);
  assert.equal(reviewMode(a), "reading");
  assert.deepEqual(a.reviewTrack.completed, { listening: 1, reading: 0, writing: 0 });
  const b = recordReviewMode(a, "ok", at);
  assert.equal(reviewMode(b), "writing");
  assert.deepEqual(b.reviewTrack.completed, { listening: 1, reading: 1, writing: 0 });
  const c = recordReviewMode(b, "ok", at);
  assert.equal(reviewMode(c), "listening");
  assert.deepEqual(c.reviewTrack.completed, { listening: 1, reading: 1, writing: 1 });
});

test("Again keeps the same skill and counts the attempt without completing it", () => {
  const reading = ensureReviewTrack({ id: "s1", reviewTrack: { next: "reading", completed: { listening: 1 }, attempts: { listening: 1 } } });
  const after = recordReviewMode(reading, "again", new Date("2026-10-01T12:00:00Z"));
  assert.equal(reviewMode(after), "reading");
  assert.equal(after.reviewTrack.completed.reading, 0);
  assert.equal(after.reviewTrack.attempts.reading, 1);
  assert.equal(after.reviewTrack.last.mode, "reading");
  assert.equal(after.reviewTrack.last.rating, "again");
  assert.equal(after.reviewTrack.last.at, "2026-10-01T12:00:00.000Z");
});

test("a valid track is returned as the same object; invalid parts are repaired", () => {
  const tracked = recordReviewMode({ id: "s" }, "ok", new Date("2026-10-01T12:00:00Z"));
  assert.equal(ensureReviewTrack(tracked), tracked);
  const repaired = ensureReviewTrack({ id: "s", reviewTrack: { next: "speaking", completed: { reading: -2, writing: "3.7" }, last: { mode: "bogus" } } });
  assert.equal(reviewMode(repaired), "listening");
  assert.deepEqual(repaired.reviewTrack.completed, { listening: 0, reading: 0, writing: 3 });
  assert.equal(repaired.reviewTrack.last, null);
  assert.equal(ensureReviewTrack(null), null);
});

test("nextSkill wraps round", () => {
  assert.deepEqual(REVIEW_MODES.map(nextSkill), ["reading", "writing", "listening"]);
  assert.equal(nextSkill("unknown"), "reading");
});

test("today's skill mix counts each due sentence's next skill", () => {
  const read = recordReviewMode(ensureReviewTrack({ id: "r" }), "ok");
  assert.deepEqual(skillMix([{ id: "a" }, { id: "b" }, read]), { listening: 2, reading: 1, writing: 0 });
  assert.deepEqual(skillMix([]), { listening: 0, reading: 0, writing: 0 });
});

// ---- Review stats (ported from Echo's test/review-stats.test.js) -------------------

const statsNow = Date.parse("2026-10-06T14:00:00Z");
const day = 86400000;
const event = (ago, rating = "ok", mode = "listening") => ({ at: new Date(statsNow - ago).toISOString(), rating, mode });

test("rolling 24h counts both grades and only valid past timestamps", () => {
  const items = [{ id: "a", reviews: [event(0), event(day - 1, "again", "reading"), event(day), event(-1), { at: "bad", rating: "ok" }, event(3, "skip")] }];
  const before = structuredClone(items);
  const s = reviewStats(items, statsNow);
  assert.equal(s.last24h, 2); assert.equal(s.total, 3); assert.equal(s.ok24h, 1); assert.equal(s.again24h, 1);
  assert.equal(s.unique24h, 1); assert.equal(s.modes.reading, 1); assert.deepEqual(items, before);
});

test("week bins partition the rolling seven-day history without duplicates", () => {
  const s = reviewStats([{ id: "a", reviews: [event(0), event(day), event(2 * day), event(7 * day - 1), event(7 * day)] }], statsNow);
  assert.equal(s.last7d, 4); assert.equal(s.days.reduce((n, d) => n + d.count, 0), 4);
  assert.equal(s.days[0].count, 1); assert.equal(s.days[1].count, 1); assert.equal(s.total, 5);
  assert.equal(s.days[0].label, "Past 24 hours"); assert.equal(s.days[1].label, "24–48 hours ago");
});

test("empty legacy records and missing skill metadata remain usable", () => {
  const s = reviewStats([{ id: "a" }, { id: "b", reviews: null }, { id: "c", reviews: [{ at: new Date(statsNow).toISOString(), rating: "ok" }] }], statsNow);
  assert.equal(s.last24h, 1); assert.equal(s.total, 1); assert.deepEqual(s.modes, { listening: 0, reading: 0, writing: 0 });
});

// ---- Anki export (ported from Echo's test/anki-schedule.test.js) ---------------------

test("exports reviewed FSRS progress to Anki card fields", () => {
  const created = Date.parse("2026-09-20T00:00:00Z") / 1000;
  const row = ankiSchedule({ due: "2026-10-01T00:00:00Z", scheduled_days: 7, reps: 4, lapses: 1, state: 2 }, created);
  assert.deepEqual(row, { type: 2, queue: 2, due: 11, interval: 7, factor: 2500, reps: 4, lapses: 1, left: 0 });
});

test("keeps short-term learning due timestamps", () => {
  const row = ankiSchedule({ due: "2026-09-20T00:01:00Z", scheduled_days: 0, reps: 1, lapses: 0, state: 1 }, 0);
  assert.equal(row.queue, 1);
  assert.equal(row.due, Date.parse("2026-09-20T00:01:00Z") / 1000);
  assert.equal(row.left, 1001);
});

test("relearning cards keep type 3; unreviewed cards export as new", () => {
  assert.equal(ankiSchedule({ due: "2026-09-20T00:10:00Z", scheduled_days: 0, reps: 5, lapses: 1, state: 3 }, 0).type, 3);
  assert.equal(ankiSchedule(ensureSchedule(sentence, now).srs, 0), null);
  assert.equal(ankiSchedule(undefined, 0), null);
});
