# -*- coding: utf-8 -*-
"""Собирает docs/testing-program.html из docs/testing-program/*.md.

Страница самодостаточна: разделы вшиты в неё как текст и рендерятся
marked.js в браузере. Если страница открыта по http(s) (GitHub Pages,
python -m http.server), она сперва пробует подтянуть свежие md из
testing-program/ рядом - тогда правка md видна без пересборки.
Флажки шагов запоминаются в localStorage, кнопка "Выгрузить акт" собирает
markdown с отметками.

    python tools\\testprog_html.py            # пересобрать
"""
import os, re, io, json, html, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "docs", "testing-program")
OUT = os.path.join(ROOT, "docs", "testing-program.html")

VARIANTS = ["ALL", "CASSA", "UNIREST", "TS", "SIZES", "SELF"]


def sections():
    out = []
    for f in sorted(os.listdir(SRC)):
        if not f.endswith(".md"):
            continue
        text = io.open(os.path.join(SRC, f), encoding="utf-8-sig").read()
        m = re.match(r"\s*<!--\s*variants:\s*([^>]*?)\s*-->", text)
        variants = m.group(1).split() if m else ["ALL"]
        title = re.search(r"^#\s+(.*)$", text, re.M)
        out.append({"file": f, "variants": variants, "title": title.group(1).strip() if title else f,
                    "text": text, "steps": text.count("- [ ]") + text.count("- [x]")})
    return out


PAGE = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Программа тестирования UAMenu</title>
<meta name="description" content="Полная программа приёмочного тестирования кассы UAMenu: синхронизация, продажи, приёмка, инвентаризация, оплаты, X/Z, отчёты, виды товара, заказы, поиск.">
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<style>
:root{
  --bg:#f6f4ee; --paper:#fffdf8; --ink:#1e1c18; --muted:#6b665c; --line:#d9d3c6;
  --accent:#8a3b12; --accent-ink:#fff; --ok:#2e7d32; --chip:#ece7db; --code:#f0ebe0;
  --mono:"Cascadia Mono","Consolas","JetBrains Mono",ui-monospace,monospace;
  --sans:"Segoe UI",system-ui,-apple-system,Roboto,sans-serif;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#17160f; --paper:#1f1d16; --ink:#ece6d8; --muted:#a39c8c; --line:#3a362c;
  --accent:#e0864f; --accent-ink:#1a120b; --ok:#7bc47f; --chip:#2b2820; --code:#272418; }}
:root[data-theme="dark"]{
  --bg:#17160f; --paper:#1f1d16; --ink:#ece6d8; --muted:#a39c8c; --line:#3a362c;
  --accent:#e0864f; --accent-ink:#1a120b; --ok:#7bc47f; --chip:#2b2820; --code:#272418; }
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 var(--sans)}
a{color:var(--accent)}
.wrap{display:grid;grid-template-columns:300px minmax(0,1fr);min-height:100vh}
nav{position:sticky;top:0;height:100vh;overflow:auto;padding:20px 16px;border-right:1px solid var(--line);background:var(--paper)}
nav h1{font-size:17px;margin:0 0 4px;letter-spacing:.01em}
nav .sub{color:var(--muted);font-size:13px;margin-bottom:14px}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 12px}
.chip{border:1px solid var(--line);background:var(--chip);border-radius:999px;padding:3px 10px;font-size:12.5px;cursor:pointer;user-select:none}
.chip[aria-pressed="true"]{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
nav input[type=search]{width:100%;padding:7px 9px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font:inherit;margin-bottom:12px}
.toc a{display:flex;justify-content:space-between;gap:8px;text-decoration:none;color:var(--ink);padding:5px 6px;border-radius:6px;font-size:14px}
.toc a:hover{background:var(--chip)}
.toc a.hidden{display:none}
.toc .n{color:var(--muted);font-variant-numeric:tabular-nums;font-size:12.5px;white-space:nowrap}
.toc .n.done{color:var(--ok)}
.tools{display:grid;gap:6px;margin-top:16px}
button{font:inherit;font-size:13.5px;padding:7px 10px;border-radius:8px;border:1px solid var(--line);background:var(--paper);color:var(--ink);cursor:pointer}
button.primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
button:focus-visible,.chip:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
main{padding:28px clamp(16px,4vw,56px) 80px;max-width:980px}
.status{color:var(--muted);font-size:13px;margin-bottom:20px}
section.part{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:8px 28px 20px;margin:0 0 22px}
section.part.hidden{display:none}
section.part .meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;color:var(--muted);font-size:12.5px;margin:14px 0 -6px}
section.part .meta .chip{cursor:default}
.md h1{font-size:24px;line-height:1.25;margin:16px 0 8px;text-wrap:balance}
.md h2{font-size:18px;margin:26px 0 8px;padding-top:12px;border-top:1px dashed var(--line)}
.md p,.md ul,.md ol{max-width:72ch}
.md code{font:13.5px var(--mono);background:var(--code);padding:1px 5px;border-radius:4px}
.md pre{background:var(--code);padding:12px 14px;border-radius:8px;overflow-x:auto}
.md pre code{background:none;padding:0}
.md table{border-collapse:collapse;margin:10px 0;font-size:14.5px;display:block;overflow-x:auto;max-width:100%}
.md th,.md td{border:1px solid var(--line);padding:5px 9px;vertical-align:top;text-align:left}
.md th{background:var(--chip)}
.md li.step{list-style:none;margin-left:-22px;display:flex;gap:9px;align-items:flex-start}
.md li.step input{margin-top:5px;accent-color:var(--accent);width:16px;height:16px;flex:none}
.md li.step.done label{color:var(--muted);text-decoration:line-through;text-decoration-color:var(--line)}
.md li.step label{cursor:pointer}
.md blockquote{margin:10px 0;padding:6px 14px;border-left:3px solid var(--accent);color:var(--muted)}
@media (max-width:860px){
  .wrap{grid-template-columns:1fr}
  nav{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line)}
  main{padding:16px}
  section.part{padding:6px 16px 16px}
}
@media (prefers-reduced-motion:no-preference){ .toc a{transition:background .12s} }
</style>
</head>
<body>
<div class="wrap">
<nav>
  <h1>Программа тестирования UAMenu</h1>
  <div class="sub">Собрано __BUILT__ · разделов __N__ · шагов __STEPS__</div>
  <div class="chips" id="variants" role="group" aria-label="Вариант кассы"></div>
  <input type="search" id="q" placeholder="Искать по тексту программы…" aria-label="Поиск">
  <div class="toc" id="toc"></div>
  <div class="tools">
    <button class="primary" id="export">Выгрузить акт (.md)</button>
    <button id="reset">Сбросить отметки</button>
    <button id="theme">Тема: авто</button>
  </div>
</nav>
<main>
  <div class="status" id="status"></div>
  <div id="parts"></div>
</main>
</div>

__TEMPLATES__

<script>
(function(){
  const SECTIONS = __MANIFEST__;
  const KEY = 'uamenu-testprog-v1';
  let state = {}; try { state = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch(e) { state = {}; }
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch(e) {} };
  let filter = 'ALL';
  const texts = {};
  for (const s of SECTIONS) texts[s.file] = document.getElementById('md-' + s.file).textContent;

  marked.use({ gfm: true, breaks: false });

  function render(){
    const parts = document.getElementById('parts'); parts.innerHTML = '';
    const toc = document.getElementById('toc'); toc.innerHTML = '';
    for (const s of SECTIONS) {
      const sec = document.createElement('section'); sec.className = 'part'; sec.id = 'sec-' + s.file; sec.dataset.file = s.file;
      const meta = document.createElement('div'); meta.className = 'meta';
      meta.append('Варианты: '); for (const v of s.variants) { const c = document.createElement('span'); c.className = 'chip'; c.textContent = v; meta.append(c); }
      const src = document.createElement('span'); src.textContent = '· ' + s.file; meta.append(src);
      const md = document.createElement('div'); md.className = 'md';
      md.innerHTML = marked.parse(texts[s.file].replace(/^\s*<!--[^>]*-->\s*/, ''));
      let i = 0;
      md.querySelectorAll('li').forEach(li => {
        const cb = li.querySelector(':scope > input[type=checkbox]');
        if (!cb) return;
        const id = s.file + '#' + (i++);
        cb.disabled = false; cb.id = 'cb-' + id.replace(/[^\w-]/g, '_'); cb.checked = !!state[id];
        li.className = 'step' + (cb.checked ? ' done' : '');
        const label = document.createElement('label'); label.htmlFor = cb.id;
        while (cb.nextSibling) label.append(cb.nextSibling);
        li.append(label);
        cb.addEventListener('change', () => { state[id] = cb.checked; if (!cb.checked) delete state[id]; save(); li.classList.toggle('done', cb.checked); counts(); });
      });
      sec.append(meta, md); parts.append(sec);
      const a = document.createElement('a'); a.href = '#sec-' + s.file; a.dataset.file = s.file;
      a.innerHTML = '<span></span><span class="n"></span>'; a.firstChild.textContent = s.title; toc.append(a);
    }
    counts(); applyFilter();
  }

  function counts(){
    let all = 0, done = 0;
    for (const s of SECTIONS) {
      const sec = document.getElementById('sec-' + s.file);
      const cbs = sec.querySelectorAll('li.step input'); const d = [...cbs].filter(c => c.checked).length;
      all += cbs.length; done += d;
      const n = document.querySelector('.toc a[data-file="' + s.file + '"] .n');
      n.textContent = cbs.length ? d + '/' + cbs.length : ''; n.classList.toggle('done', cbs.length && d === cbs.length);
    }
    document.getElementById('status').textContent = 'Фильтр: ' + filter + ' · отмечено ' + done + ' из ' + all + ' шагов' + (location.protocol.startsWith('http') ? ' · разделы подтягиваются из testing-program/*.md' : ' · разделы вшиты в страницу');
  }

  function applyFilter(){
    const q = document.getElementById('q').value.trim().toLowerCase();
    for (const s of SECTIONS) {
      const okV = filter === 'ALL' || s.variants.includes('ALL') || s.variants.includes(filter);
      const okQ = !q || texts[s.file].toLowerCase().includes(q);
      document.getElementById('sec-' + s.file).classList.toggle('hidden', !(okV && okQ));
      document.querySelector('.toc a[data-file="' + s.file + '"]').classList.toggle('hidden', !(okV && okQ));
    }
    counts();
  }

  const vbox = document.getElementById('variants');
  for (const v of __VARIANTS__) {
    const b = document.createElement('button'); b.className = 'chip'; b.textContent = v === 'ALL' ? 'Все' : v; b.setAttribute('aria-pressed', v === 'ALL');
    b.addEventListener('click', () => { filter = v; vbox.querySelectorAll('.chip').forEach(c => c.setAttribute('aria-pressed', c === b)); applyFilter(); });
    vbox.append(b);
  }
  document.getElementById('q').addEventListener('input', applyFilter);
  document.getElementById('reset').addEventListener('click', () => { if (confirm('Снять все отметки?')) { state = {}; save(); render(); } });
  document.getElementById('export').addEventListener('click', () => {
    const lines = ['# Акт тестирования UAMenu', '', 'Дата: ' + new Date().toLocaleString('ru-RU'), 'Вариант кассы: ' + filter, ''];
    for (const s of SECTIONS) {
      if (document.getElementById('sec-' + s.file).classList.contains('hidden')) continue;
      let i = 0;
      const body = texts[s.file].replace(/^\s*<!--[^>]*-->\s*/, '').replace(/^(\s*)- \[[ x]\]/gm, (m, sp) => sp + '- [' + (state[s.file + '#' + (i++)] ? 'x' : ' ') + ']');
      lines.push(body.trim(), '');
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'uamenu-test-act-' + new Date().toISOString().slice(0, 10) + '.md'; a.click();
  });
  const tbtn = document.getElementById('theme'); const modes = ['auto', 'light', 'dark']; let mode = 'auto';
  try { mode = localStorage.getItem(KEY + ':theme') || 'auto'; } catch(e) {}
  const applyTheme = () => { if (mode === 'auto') delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = mode; tbtn.textContent = 'Тема: ' + ({auto:'авто', light:'светлая', dark:'тёмная'})[mode]; };
  tbtn.addEventListener('click', () => { mode = modes[(modes.indexOf(mode) + 1) % 3]; try { localStorage.setItem(KEY + ':theme', mode); } catch(e) {} applyTheme(); });
  applyTheme();

  render();

  // Динамические вставки: при показе по http подтянуть свежие md рядом со страницей
  if (location.protocol.startsWith('http')) {
    Promise.all(SECTIONS.map(s => fetch('testing-program/' + s.file, { cache: 'no-store' }).then(r => r.ok ? r.text() : null).catch(() => null)))
      .then(res => { let changed = false; res.forEach((t, k) => { if (t && t !== texts[SECTIONS[k].file]) { texts[SECTIONS[k].file] = t; changed = true; } }); if (changed) render(); });
  }
})();
</script>
</body>
</html>
"""


def main():
    secs = sections()
    templates = "\n".join(
        '<script type="text/plain" id="md-%s">%s</script>' % (s["file"], s["text"].replace("</script", "<\\/script"))
        for s in secs)
    manifest = json.dumps([{"file": s["file"], "title": s["title"], "variants": s["variants"]} for s in secs],
                          ensure_ascii=False)
    page = (PAGE.replace("__TEMPLATES__", templates).replace("__MANIFEST__", manifest)
            .replace("__VARIANTS__", json.dumps(VARIANTS)).replace("__BUILT__", datetime.date.today().isoformat())
            .replace("__N__", str(len(secs))).replace("__STEPS__", str(sum(s["steps"] for s in secs))))
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(page)
    print("%s: %d разделов, %d шагов, %d КБ" % (os.path.relpath(OUT, ROOT), len(secs), sum(s["steps"] for s in secs),
                                                 len(page.encode("utf-8")) // 1024))


if __name__ == "__main__":
    main()
