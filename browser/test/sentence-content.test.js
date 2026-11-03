import test from 'node:test';
import assert from 'node:assert/strict';
import {replaceSentenceContent} from '../jp-core.js';
test('replacing content preserves identity, timestamps and every review field',()=>{
 const old={id:'card',sourceLang:'en',targetLang:'ja',createdAt:'2020-01-01',echoCount:12,reviews:[{rating:'ok'}],srs:{due:'tomorrow'},reviewTrack:{completed:{listening:2}}};
 const next=replaceSentenceContent(old,{source:'Station',casual:'駅【えき】',polite:'駅【えき】です。'},new Date('2026-10-02'));
 for(const key of ['id','createdAt','echoCount','reviews','srs','reviewTrack'])assert.deepEqual(next[key],old[key]);assert.equal(next.plainTarget,'駅');assert.equal(next.plainPoliteTarget,'駅です。');assert.equal(old.source,undefined);
});

test('a reading covers its kanji only: kana it repeats from just before are trimmed',async()=>{
 const {normalizeFurigana,rubySegments}=await import('../jp-core.js');
 assert.equal(normalizeFurigana('標準【ひょうじゅん】のやり方【やりかた】に合【あ】わせます。'),'標準【ひょうじゅん】のやり方【かた】に合【あ】わせます。');
 assert.equal(normalizeFurigana('お茶【おちゃ】とご飯【ごはん】'),'お茶【ちゃ】とご飯【はん】');
 assert.equal(normalizeFurigana('ここ子供【こども】'),'ここ子供【こども】');
 assert.equal(rubySegments('やり方【やりかた】').map(s=>s.reading||s.text).join(''),'やりかた');
});
