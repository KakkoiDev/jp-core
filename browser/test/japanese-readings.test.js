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

test('irregular kuru readings outrank the standalone rai prefix for all modern forms',()=>{
 const words=[{w:'来',r:'らい',pos:['pref']},{w:'来る',r:'くる',pos:['vk']},{w:'来る',r:'きたる',pos:['adj-pn']},{w:'来年',r:'らいねん',pos:['n']},{w:'将来',r:'しょうらい',pos:['n']}];
 const native=Intl.Segmenter;
 try{for(const segmenter of [native,undefined]){
 Intl.Segmenter=segmenter;const resolve=createReadingResolver(words);
 for(const [suffix,reading] of [['た','き'],['て','き'],['ます','き'],['ました','き'],['たい','き'],['なさい','き'],['ながら','き'],['にくい','き'],['そう','き'],['ちゃった','き'],['すぎる','き'],['る','く'],['れば','く'],['ない','こ'],['なくて','こ'],['なかった','こ'],['なければ','こ'],['なきゃ','こ'],['よう','こ'],['い','こ'],['られる','こ'],['れる','こ'],['させる','こ'],['ず','こ'],['ぬ','こ']]){
  const result=resolve(`来【らい】${suffix}`);assert.equal(result.text,`来【${reading}】${suffix}`,suffix);assert.equal(result.issues.length,0,suffix);
 }
 assert.equal(resolve('来年【らいねん】も来【らい】た。').text,'来年【らいねん】も来【き】た。');
 assert.equal(resolve('将来【しょうらい】').text,'将来【しょうらい】');
 assert.equal(resolve('来【きた】る五月').text,'来【きた】る五月');
 }}finally{Intl.Segmenter=native}
});
test('kuru compounds retain their prefix and inflect as one dictionary word',()=>{
 const resolve=createReadingResolver([{w:'来',r:'らい',pos:['pref']},{w:'来る',r:'くる',pos:['vk']},{w:'やって来る',r:'やってくる',pos:['vk']}]);
 assert.equal(resolve('やって来【らい】た').text,'やって来【き】た');
 assert.equal(resolve('やって来【らい】ない').text,'やって来【こ】ない');
});

test("い-adjective and ichidan stems take すぎる, そう and さ: 多すぎる is おお, never the prefix 多 (た)",()=>{
 const resolve=createReadingResolver([{w:"多",r:"た",pos:["n","pref"]},{w:"多い",r:"おおい",pos:["adj-i"]},{w:"高い",r:"たかい",pos:["adj-i"]},{w:"食べる",r:"たべる",pos:["v1","vt"]},{w:"項目",r:"こうもく"}]);
 assert.equal(resolve("項目が多すぎます。").text,"項目【こうもく】が多【おお】すぎます。");
 assert.equal(resolve("高そうだ").text,"高【たか】そうだ");
 assert.equal(resolve("高さ").text,"高【たか】さ");
 assert.equal(resolve("食べすぎた").text,"食【た】べすぎた");
});

test("何 is なに or なん by what follows it, and a wrong saved reading is corrected",()=>{
 const resolve=createReadingResolver([{w:"何",r:"なに"},{w:"何",r:"なん"},{w:"苗字",r:"みょうじ"}]);
 assert.equal(resolve("苗字【みょうじ】は何【なん】？").text,"苗字【みょうじ】は何【なに】？");
 assert.equal(resolve("何を").text,"何【なに】を");assert.equal(resolve("何か").text,"何【なに】か");
 assert.equal(resolve("何ですか").text,"何【なん】ですか");assert.equal(resolve("何の").text,"何【なん】の");
});

test('common compounds missing from the compact dictionary repair saved ruby as a unit',()=>{
 const resolve=createReadingResolver([
  {w:'見積もり',r:'みつもり'},{w:'書く',r:'かく',pos:['v5k']},
  {w:'認知',r:'にんち'},{w:'負荷',r:'ふか'},
  {w:'読む',r:'よむ',pos:['v5m']},{w:'本日',r:'ほんじつ'},
  {w:'用語',r:'ようご'},{w:'残る',r:'のこる',pos:['v5r']},
 ]);
 for(const [stored,expected] of [
  ['見積【みつ】を書【か】いた。','見積【みつもり】を書【か】いた。'],
  ['見積【みつ】もりを書【か】いた。','見積【みつ】もりを書【か】いた。'],
  ['認知【にんち】的な過負荷【ふか】。','認知的【にんちてき】な過負荷【かふか】。'],
  ['本日着任しました。','本日【ほんじつ】着任【ちゃくにん】しました。'],
  ['既読【よ】つけといて。','既読【きどく】つけといて。'],
  ['用語の誤用が残っています。','用語【ようご】の誤用【ごよう】が残【のこ】っています。'],
 ]){
  assert.deepEqual(resolve(stored),{text:expected,issues:[]});
  validateReadingCorrection(stored,expected);
  assert.deepEqual(resolve(expected),{text:expected,issues:[]});
 }
});
