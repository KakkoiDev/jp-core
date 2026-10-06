import test from 'node:test';import assert from 'node:assert/strict';
import {createReadingResolver,readingText,validateReadingCorrection} from '../japanese-readings.js';
test('dictionary readings and speech share the same notation',()=>{const resolve=createReadingResolver([{w:'重複',r:'ちょうふく'},{w:'食べる',r:'たべる'}]);assert.equal(resolve('重複【じゅうふく】').text,'重複【ちょうふく】');assert.equal(resolve('食べた').text,'食【た】べた');assert.equal(readingText('重複【ちょうふく】'),'ちょうふく');assert.throws(()=>validateReadingCorrection('重複','複製【ふくせい】'),/changed/)});

test('言う wins over the standalone noun 言 in the reported migration sentence',()=>{
 const resolve=createReadingResolver([{w:'言',r:'げん'},{w:'言う',r:'いう'},{w:'移行',r:'いこう'},{w:'半分',r:'はんぶん'},{w:'終わる',r:'おわる'}]);
 const sentence='ざっくり言【げん】うと、移行【いこう】は半分【はんぶん】終【お】わっています。';
 const corrected=resolve(sentence).text;
 assert.equal(corrected,'ざっくり言【い】うと、移行【いこう】は半分【はんぶん】終【お】わっています。');
 assert.equal(readingText(corrected),'ざっくりいうと、いこうははんぶんおわっています。');
});
