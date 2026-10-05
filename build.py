"""Render data/news.json -> docs/index.html (single self-contained page)."""
import json
from jinja2 import Template

TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily Industry News</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--text:#14181f;--muted:#667085;--line:#e4e7ec;--accent:#0b5cff;--chip:#eef2ff}
:root[data-theme=dark]{--bg:#0f1218;--card:#181d26;--text:#e8ebf0;--muted:#98a2b3;--line:#2a313d;--accent:#6ea0ff;--chip:#222b3d}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,Segoe UI,sans-serif;background:var(--bg);color:var(--text)}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 20px;z-index:5}
.top{display:flex;gap:12px;align-items:center;flex-wrap:wrap}h1{font-size:18px;margin:0;flex:1}
.meta{color:var(--muted);font-size:12px}
.tabs{display:flex;gap:8px;margin-top:10px}.tab{padding:6px 14px;border:1px solid var(--line);border-radius:20px;background:var(--card);color:var(--text);cursor:pointer}
.tab.on{background:var(--accent);color:#fff;border-color:var(--accent)}
input,select,button.t{padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--text)}
main{display:grid;grid-template-columns:1fr 1fr;gap:20px;padding:20px;max-width:1400px;margin:auto}
@media(max-width:800px){main{grid-template-columns:1fr}}
h2{font-size:15px;margin:0 0 10px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted)}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:10px}
.card a{color:var(--text);font-weight:600;text-decoration:none}.card a:hover{color:var(--accent)}
.sub{color:var(--muted);font-size:13px;margin:4px 0}.row{font-size:12px;color:var(--muted);display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.chip{background:var(--chip);color:var(--accent);padding:1px 8px;border-radius:10px}
.empty{color:var(--muted)}
</style></head><body>
<header><div class="top"><h1>Daily Industry News</h1>
<input id="q" placeholder="Search…"><select id="st"><option value="">All sub-topics</option></select>
<button class="t" id="th">Dark mode</button></div>
<div class="meta">Updated {{ updated }} IST · {{ "Gemini-classified" if llm else "keyword-classified" }}</div>
<div class="tabs"><button class="tab on" data-t="auto">Auto &amp; Auto Components</button>
<button class="tab" data-t="electrical_electronics">Electrical Equipment &amp; Electronics</button></div></header>
{% for ind in ["auto","electrical_electronics"] %}
<main data-ind="{{ ind }}"{% if ind != "auto" %} hidden{% endif %}>
{% for reg, label in [("india","India"),("global","Global")] %}
<section><h2>{{ label }} ({{ news[ind ~ "_" ~ reg]|length }})</h2>
{% for a in news[ind ~ "_" ~ reg] %}
<div class="card" data-s="{{ a.subtopic }}" data-q="{{ (a.title ~ ' ' ~ a.source ~ ' ' ~ a.why_it_matters)|lower|e }}">
<a href="{{ a.url }}" target="_blank" rel="noopener">{{ a.title }}</a>
{% if a.why_it_matters %}<div class="sub">{{ a.why_it_matters }}</div>{% elif a.summary %}<div class="sub">{{ a.summary[:160] }}…</div>{% endif %}
<div class="row"><span>{{ a.source }}</span><span class="ago" data-t="{{ a.published }}"></span><span class="chip">{{ a.subtopic }}</span></div></div>
{% else %}<div class="empty">No articles in the last 36 hours.</div>{% endfor %}
</section>{% endfor %}</main>{% endfor %}
<script>
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
$$('.ago').forEach(e=>{const h=(Date.now()-new Date(e.dataset.t))/36e5;e.textContent=h<1?'<1h ago':h<24?Math.round(h)+'h ago':Math.round(h/24)+'d ago'});
const sel=$('#st');[...new Set($$('.card').map(c=>c.dataset.s))].sort().forEach(s=>sel.add(new Option(s,s)));
function filt(){const q=$('#q').value.toLowerCase(),s=sel.value;$$('.card').forEach(c=>c.hidden=!((!q||c.dataset.q.includes(q))&&(!s||c.dataset.s===s)))}
$('#q').oninput=filt;sel.onchange=filt;
$$('.tab').forEach(b=>b.onclick=()=>{$$('.tab').forEach(x=>x.classList.toggle('on',x===b));$$('main').forEach(m=>m.hidden=m.dataset.ind!==b.dataset.t)});
const root=document.documentElement;try{if(localStorage.th==='dark')root.dataset.theme='dark'}catch(e){}
$('#th').onclick=()=>{root.dataset.theme=root.dataset.theme==='dark'?'':'dark';try{localStorage.th=root.dataset.theme}catch(e){}};
</script></body></html>"""


def main():
    news = json.load(open("data/news.json", encoding="utf-8"))
    meta = news.pop("_meta")
    from datetime import datetime, timezone, timedelta
    ist = datetime.fromisoformat(meta["generated"]).astimezone(timezone(timedelta(hours=5, minutes=30)))
    html = Template(TEMPLATE).render(news=news, llm=meta["llm"], updated=ist.strftime("%d %b %Y, %H:%M"))
    open("docs/index.html", "w", encoding="utf-8").write(html)
    print("Wrote docs/index.html")


if __name__ == "__main__":
    main()
