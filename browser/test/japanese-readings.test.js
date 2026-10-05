import test from 'node:test';import assert from 'node:assert/strict';
import {createReadingResolver,readingText,validateReadingCorrection} from '../japanese-readings.js';
test('dictionary readings and speech share the same notation',()=>{const resolve=createReadingResolver([{w:'重複',r:'ちょうふく'},{w:'食べる',r:'たべる'}]);assert.equal(resolve('重複【じゅうふく】').text,'重複【ちょうふく】');assert.equal(resolve('食べた').text,'食【た】べた');assert.equal(readingText('重複【ちょうふく】'),'ちょうふく');assert.throws(()=>validateReadingCorrection('重複','複製【ふくせい】'),/changed/)});
