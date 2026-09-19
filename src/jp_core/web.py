"""Framework-neutral HTML and assets for Japanese furigana."""
from __future__ import annotations

import html

from jp_core.furigana import parse

FURIGANA_CSS = """.jp-core-furigana-hidden rt{display:none}
.jp-core-furigana-toggle{cursor:pointer}
@media print{.jp-core-furigana-toggle{display:none}}"""

FURIGANA_TOGGLE_JS = """(()=>{const k="jp-core-furigana-hidden",c=k,b=document.body;
const apply=v=>{b.classList.toggle(c,v);localStorage.setItem(k,v?"1":"0")};
document.querySelectorAll("[data-jp-core-furigana-toggle]").forEach(x=>{
x.addEventListener("click",()=>apply(!b.classList.contains(c)));
x.setAttribute("aria-pressed",String(!b.classList.contains(c)))});
apply(localStorage.getItem(k)==="1")})();"""


def ruby_html(value: str) -> str:
    """Render canonical notation safely as semantic ruby HTML."""
    parts = []
    for token in parse(value):
        base = html.escape(token.base)
        if token.reading is None:
            parts.append(base)
        else:
            parts.append(f"<ruby>{base}<rt>{html.escape(token.reading)}</rt></ruby>")
    return "".join(parts)


def toggle_button(*, label: str = "ふりがな", button_id: str | None = None) -> str:
    identity = f' id="{html.escape(button_id)}"' if button_id else ""
    return (
        f'<button type="button"{identity} class="jp-core-furigana-toggle" '
        f'data-jp-core-furigana-toggle aria-pressed="true">{html.escape(label)}</button>'
    )
