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

test('longest compound reading wins over shorter entries and inflects as a unit',()=>{
 const words=[{w:'話',r:'はなし'},{w:'合',r:'ごう'},{w:'合う',r:'あう',pos:['v5u']},{w:'話す',r:'はなす',pos:['v5s']},{w:'話し合う',r:'はなしあう',pos:['v5u']}];
 const resolve=createReadingResolver(words);
 assert.equal(resolve('話【はなし】し合【ごう】う').text,'話【はな】し合【あ】う');
 assert.equal(resolve('話【はなし】し合【ごう】います').text,'話【はな】し合【あ】います');
 assert.equal(resolve('話【はなし】し合【ごう】った').text,'話【はな】し合【あ】った');
});
test('an ambiguous longer entry is not replaced by a convenient shorter reading',()=>{
 const resolve=createReadingResolver([{w:'日本',r:'にほん'},{w:'日本語',r:'にほんご'},{w:'日本語',r:'にっぽんご'}]);
 const result=resolve('日本語【にほんご】');assert.equal(result.text,'日本語【にほんご】');assert.ok(result.issues.length);
});

test('longest compound crosses tokenizer splits instead of trusting isolated kanji',()=>{
 const native=Intl.Segmenter;
 try{
  Intl.Segmenter=class {segment(text){return [...text].map((segment,index)=>({segment,index}))}};
  const resolve=createReadingResolver([{w:'話',r:'はなし'},{w:'合',r:'ごう'},{w:'話し合う',r:'はなしあう',pos:['v5u']}]);
  assert.equal(resolve('話【はなし】し合【ごう】う').text,'話【はな】し合【あ】う');
 }finally{Intl.Segmenter=native}
});

 test('special iku conjugations do not use the noun gyou reading',()=>{
 const resolve=createReadingResolver([{w:'行',r:'ぎょう',pos:['n']},{w:'行く',r:'いく',pos:['v5k-s','vi']},{w:'行う',r:'おこなう',pos:['v5u','vt']}]);
 for(const suffix of ['く','きます','かない','ける','こう','った','って']){
  assert.equal(resolve(`行【ぎょう】${suffix}`).text,`行【い】${suffix}`,suffix);
 }
 assert.equal(resolve('行【ぎょう】を').text,'行【ぎょう】を');
 assert.equal(resolve('行【おこな】った').text,'行【おこな】った');
 assert.equal(resolve('行【ぎょう】いました').text,'行【おこな】いました');
 });

 test('speech hints distinguish lexical ha and he from particles',async()=>{
 const {speechText}=await import('../japanese-readings.js');
 assert.equal(speechText('ログ吐【は】いてる？'),'ログハいてる？');
 assert.equal(speechText('彼【かれ】は部屋【へや】へ行【い】く。'),'カレはヘヤへイく。');
 assert.equal(readingText('吐【は】いてる'),'はいてる');
 });

test('adjectives win over isolated kanji even when the browser splits the word',()=>{
 const native=Intl.Segmenter;
 try{
 Intl.Segmenter=class {segment(text){return [...text].map((segment,index)=>({segment,index}))}};
 const resolve=createReadingResolver([{w:'難',r:'なん',pos:['n']},{w:'難い',r:'かたい',pos:['adj-i']},{w:'難しい',r:'むずかしい',pos:['adj-i']},{w:'高',r:'こう',pos:['n']},{w:'高い',r:'たかい',pos:['adj-i']}]);
 for(const ending of ['い','くない','かった','ければ'])assert.equal(resolve(`難【なん】し${ending}`).text,`難【むずか】し${ending}`);
 assert.equal(resolve('高【こう】かった').text,'高【たか】かった');
 }finally{Intl.Segmenter=native}
});
test('dictionary special regular categories participate in conjugation matching',()=>{
 for(const [w,r,pos,input,expected] of [
 ['有る','ある','v5r-i','有【ゆう】った','有【あ】った'],
 ['問う','とう','v5u-s','問【もん】わない','問【と】わない'],
 ['呉れる','くれる','v1-s','呉【ご】れた','呉【く】れた']]){
 const resolve=createReadingResolver([{w:w[0],r:'ご',pos:['n']},{w,r,pos:[pos]}]);assert.equal(resolve(input).text,expected);
 }
});

test('onaji and muzukashii do not depend on native tokenizer availability or boundaries',()=>{
 const native=Intl.Segmenter;
 try{
 for(const segmenter of [undefined,class {segment(text){return [{segment:text,index:0}]}}]){
 Intl.Segmenter=segmenter;
 const resolve=createReadingResolver([{w:'同',r:'どう',pos:['n']},{w:'同じ',r:'おなじ',pos:['adj-f']},{w:'難',r:'なん',pos:['n']},{w:'難しい',r:'むずかしい',pos:['adj-i']}]);
 assert.equal(resolve('同【どう】じような').text,'同【おな】じような');
 assert.equal(resolve('難【なん】しいところです').text,'難【むずか】しいところです');
 }
 }finally{Intl.Segmenter=native}
});
