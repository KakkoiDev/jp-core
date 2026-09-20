export const SCHEMA_VERSION = 1;
// The lookahead rejects an annotation with nothing in it; `stray` then removes
// it. A model emits 【】 when it declines to supply a reading, and letting it
// through puts literal brackets on screen and reads them aloud.
const notation = /([\u3400-\u4dbf\u4e00-\u9fff々]+)【(?!\s*】)([^】]+)】/g;
const stray = /【[^】]*】/g;
const escapeHtml = value => value.replace(/[&<>"']/g, ch => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));

export function normalizeFurigana(value = "") {
  let out = "", offset = 0;
  for (const match of value.matchAll(notation)) {
    out += value.slice(offset, match.index).replace(stray, "");
    out += match[0];
    offset = match.index + match[0].length;
  }
  return out + value.slice(offset).replace(stray, "");
}

export function stripFurigana(value = "") {
  return value.replace(stray, "");
}

export function rubyHtml(value = "") {
  value = normalizeFurigana(value);
  let out = "", offset = 0;
  for (const match of value.matchAll(notation)) {
    out += escapeHtml(value.slice(offset, match.index));
    out += "<ruby>" + escapeHtml(match[1]) + "<rt>" + escapeHtml(match[2]) + "</rt></ruby>";
    offset = match.index + match[0].length;
  }
  return out + escapeHtml(value.slice(offset));
}

export function validateTranslation(result) {
  const japanese = normalizeFurigana(String(result?.japanese || "").trim());
  if (!japanese || !/[\u3040-\u30ff\u3400-\u9fff]/.test(japanese)) throw new Error("DeepSeek did not return a Japanese sentence.");
  return japanese;
}

export function createSentence(english, japanese, now = new Date(), id = crypto.randomUUID()) {
  return {id,english:english.trim(),japanese:japanese.trim(),plainJapanese:stripFurigana(japanese).trim(),echoCount:0,createdAt:now.toISOString(),updatedAt:now.toISOString(),translationProvider:"deepseek",schemaVersion:SCHEMA_VERSION};
}

export function mergeSentences(current, incoming) {
  const merged = new Map(current.map(item => [item.id, item]));
  for (const candidate of incoming) {
    if (!candidate?.id || !candidate.english || !candidate.japanese) continue;
    const old = merged.get(candidate.id);
    if (!old) { merged.set(candidate.id, candidate); continue; }
    const newest = Date.parse(candidate.updatedAt) > Date.parse(old.updatedAt) ? candidate : old;
    merged.set(candidate.id, {...newest,echoCount:Math.max(Number(old.echoCount)||0,Number(candidate.echoCount)||0),createdAt:Date.parse(old.createdAt)<=Date.parse(candidate.createdAt)?old.createdAt:candidate.createdAt});
  }
  return [...merged.values()];
}

export function exportBackup(sentences, preferences = {}) {
  const {apiKey, ...safe} = preferences;
  return {schemaVersion:SCHEMA_VERSION,exportedAt:new Date().toISOString(),sentences,preferences:safe};
}
