// End-to-end tests for the browser-distribution scenarios in SCENARIOS.md: one test per scenario, named after its
// title, through the modules' public exports as a static application imports them.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createSentence, exportBackup, mergeSentences, replaceSentenceContent, rubyHtml} from '../jp-core.js';
import {createJapaneseWordMatcher} from '../japanese-words.js';
import {createReadingResolver, readingText} from '../japanese-readings.js';
import {validateGrammarAnalysis} from '../grammar-spans.js';

test('The browser module renders the same ruby as Python', () => {
  // Given annotated text with an HTML tag / When the browser module renders it
  // Then the HTML is exactly what jp_core.web.ruby_html renders (asserted in tests/test_scenarios.py)
  assert.equal(rubyHtml('<b>日本語【にほんご】'), '&lt;b&gt;<ruby>日本語<rt>にほんご</rt></ruby>');
});

test('A backup round-trips without losing review history', () => {
  // Given a reviewed sentence on this device
  const reviewed = {...createSentence('It is a book.', '本【ほん】です。', new Date('2026-01-01'), 'mine'),
    reviews: [{at: '2026-01-02', rating: 'ok'}], srs: {reps: 5, due: '2027-01-01'}};
  // When a JSON backup holding an unreviewed copy of the same sentence is parsed and merged in
  const copy = {...createSentence('It is a book.', '本 です。', new Date('2025-06-01'), 'starter'), updatedAt: '2026-12-01'};
  const backup = JSON.parse(JSON.stringify(exportBackup([copy], {apiKey: 'never exported'})));
  assert.equal(backup.preferences.apiKey, undefined);
  const merged = mergeSentences([reviewed], backup.sentences);
  // Then one sentence remains with its reviews and scheduling
  assert.equal(merged.length, 1);
  assert.equal(merged[0].id, 'mine');
  assert.deepEqual(merged[0].reviews, reviewed.reviews);
  assert.deepEqual(merged[0].srs, reviewed.srs);
});

test('Rewriting a sentence keeps its reviews', () => {
  const old = {id: 'card', sourceLang: 'en', targetLang: 'ja', createdAt: '2020-01-01', echoCount: 12,
    reviews: [{rating: 'ok'}], srs: {due: 'tomorrow'}};
  const next = replaceSentenceContent(old, {source: 'Station', casual: '駅【えき】', polite: '駅【えき】です。'}, new Date('2026-10-02'));
  assert.equal(next.source, 'Station');
  assert.equal(next.plainTarget, '駅');
  assert.equal(next.plainPoliteTarget, '駅です。');
  for (const key of ['id', 'createdAt', 'echoCount', 'reviews', 'srs']) assert.deepEqual(next[key], old[key]);
});

test('Look up dictionary words in a sentence', () => {
  const {wordSpans} = createJapaneseWordMatcher([{id: 6, w: 'パン', r: 'パン', pos: ['n']}, {id: 7, w: '食べる', r: 'たべる', pos: ['v1']}]);
  const spans = wordSpans('パンを食べます。');
  assert.deepEqual(spans.map(span => span.id), [6, 7]);
  assert.equal(spans[1].end, 7);
});

test('Correct a wrong reading from the dictionary', () => {
  const resolve = createReadingResolver([{w: '重複', r: 'ちょうふく'}]);
  const result = resolve('重複【じゅうふく】');
  assert.equal(result.text, '重複【ちょうふく】');
  assert.equal(readingText(result.text), 'ちょうふく');
});

test('A grammar analysis that misquotes the sentence is dropped', () => {
  const result = validateGrammarAnalysis('本を読みます。', {matches: [
    {id: 'を', quote: 'を'}, {id: 'ます', quote: '読みます'}, {id: 'invented', quote: '本'}, {id: 'を', quote: 'が'},
  ]}, [{id: 'を'}, {id: 'ます'}]);
  assert.deepEqual(result.grammar, ['を', 'ます']);
  assert.deepEqual(result.spans.map(span => [span.start, span.end]), [[1, 2], [2, 6]]);
});
