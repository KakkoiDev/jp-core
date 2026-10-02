import test from 'node:test';
import assert from 'node:assert/strict';
import {replaceSentenceContent} from '../jp-core.js';
test('replacing content preserves identity, timestamps and every review field',()=>{
 const old={id:'card',sourceLang:'en',targetLang:'ja',createdAt:'2020-01-01',echoCount:12,reviews:[{rating:'ok'}],srs:{due:'tomorrow'},reviewTrack:{completed:{listening:2}}};
 const next=replaceSentenceContent(old,{source:'Station',casual:'駅【えき】',polite:'駅【えき】です。'},new Date('2026-10-02'));
 for(const key of ['id','createdAt','echoCount','reviews','srs','reviewTrack'])assert.deepEqual(next[key],old[key]);assert.equal(next.plainTarget,'駅');assert.equal(next.plainPoliteTarget,'駅です。');assert.equal(old.source,undefined);
});
