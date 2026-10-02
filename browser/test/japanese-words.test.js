import test from 'node:test';
import assert from 'node:assert/strict';
import {createJapaneseWordMatcher} from '../japanese-words.js';
const words=[{id:1,w:'起きる',r:'おきる',pos:['v1']},{id:2,w:'置く',r:'おく',pos:['v5k']},{id:3,w:'お',r:'お',pos:['pref']},{id:4,w:'ラン',r:'ラン',pos:['n']},{id:5,w:'ボー',r:'ボー',pos:['n']},{id:6,w:'パン',r:'パン',pos:['n']},{id:7,w:'食べる',r:'たべる',pos:['v1']}];
const {wordSpans,wordsIn}=createJapaneseWordMatcher(words);
test('kana polite verbs expose their entire surface and ambiguous dictionary choices',()=>{const hits=wordSpans('おきます。');assert.equal(hits.length,1);assert.equal(hits[0].end,4);assert.deepEqual(new Set(hits[0].ids),new Set([1,2]))});
test('kanji verbs cover the kanji plus polite suffix',()=>{const h=wordSpans('起きました。')[0];assert.equal(h.end,5);assert.equal(h.id,1)});
test('katakana names stay whole and never produce definitions of substrings',()=>{for(const text of ['ランボー','ランボ']){const hits=wordSpans(text);assert.equal(hits.length,1);assert.equal(hits[0].end,text.length);assert.equal(hits[0].id,null);assert.equal(wordsIn(text).size,0)}});
test('whole known loanwords retain dictionary lookup beside particles and inflected verbs',()=>{const spans=wordSpans('パンを食べます。');assert.equal(spans[0].id,6);assert.equal(spans[1].id,7);assert.equal(spans[1].end,7)});
