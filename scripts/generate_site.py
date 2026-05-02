#!/usr/bin/env python3
"""Generate a static Linkbook index suitable for GitHub Pages."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LINKS = ROOT / "links.json"
DEFAULT_OUT = ROOT / "site"


def parse_dt(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return datetime.min.replace(tzinfo=timezone.utc)


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "untagged"


def domain(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def normalize_link(link: dict) -> dict:
    tags = sorted({str(t).strip().lower() for t in link.get("tags", []) if str(t).strip()})
    saved_at = link.get("saved_at", "")
    dt = parse_dt(saved_at)
    return {
        "id": link.get("id", ""),
        "url": link.get("url", ""),
        "original_url": link.get("original_url", ""),
        "title": link.get("title") or link.get("url", "Untitled"),
        "description": link.get("description", ""),
        "category": link.get("category", "uncategorized"),
        "tags": tags,
        "saved_at": saved_at,
        "saved_date": dt.strftime("%Y-%m-%d") if dt != datetime.min.replace(tzinfo=timezone.utc) else "",
        "saved_month": dt.strftime("%Y-%m") if dt != datetime.min.replace(tzinfo=timezone.utc) else "",
        "domain": domain(link.get("url", "")),
    }


def render_index(links: list[dict]) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    tags = Counter(t for link in links for t in link["tags"])
    categories = Counter(link["category"] for link in links)
    months = Counter(link["saved_month"] for link in links if link["saved_month"])
    days = defaultdict(int)
    for link in links:
        if link["saved_date"]:
            days[link["saved_date"]] += 1

    links_json = json.dumps(links, ensure_ascii=False).replace("</", "<\\/")
    top_tags = sorted(tags.items(), key=lambda item: (-item[1], item[0]))
    category_items = sorted(categories.items(), key=lambda item: (-item[1], item[0]))
    month_items = sorted(months.items(), reverse=True)

    tag_buttons = "\n".join(
        f'<button class="chip" data-filter-type="tag" data-filter-value="{escape(tag)}">#{escape(tag)} <span>{count}</span></button>'
        for tag, count in top_tags
    ) or '<p class="muted">No tags yet.</p>'
    category_options = "\n".join(
        f'<option value="{escape(cat)}">{escape(cat)} ({count})</option>' for cat, count in category_items
    )
    month_options = "\n".join(
        f'<option value="{escape(month)}">{escape(month)} ({count})</option>' for month, count in month_items
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Linkbook</title>
  <style>
    :root {{ color-scheme: light dark; --bg:#0f172a; --panel:#111827; --muted:#94a3b8; --text:#e5e7eb; --accent:#38bdf8; --line:#243044; }}
    @media (prefers-color-scheme: light) {{ :root {{ --bg:#f8fafc; --panel:#ffffff; --muted:#64748b; --text:#0f172a; --accent:#0369a1; --line:#dbe3ef; }} }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:var(--bg); color:var(--text); }}
    header {{ padding:42px 18px 22px; max-width:1120px; margin:auto; }}
    h1 {{ margin:0; font-size:clamp(2rem, 4vw, 4rem); letter-spacing:-.05em; }}
    .sub {{ color:var(--muted); margin-top:8px; }}
    main {{ display:grid; grid-template-columns: 280px 1fr; gap:20px; max-width:1120px; margin:0 auto 56px; padding:0 18px; }}
    aside, .toolbar, .link {{ background:var(--panel); border:1px solid var(--line); border-radius:18px; box-shadow: 0 10px 30px rgba(0,0,0,.08); }}
    aside {{ padding:16px; height:max-content; position:sticky; top:14px; }}
    .toolbar {{ padding:14px; margin-bottom:14px; display:grid; grid-template-columns: 1fr 180px 150px; gap:10px; }}
    input, select {{ width:100%; border:1px solid var(--line); background:transparent; color:var(--text); border-radius:12px; padding:11px 12px; font:inherit; }}
    .stats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:14px 0 16px; }}
    .stat {{ border:1px solid var(--line); border-radius:14px; padding:10px; }}
    .stat b {{ display:block; font-size:1.3rem; }}
    .stat span, .muted {{ color:var(--muted); }}
    .chips {{ display:flex; flex-wrap:wrap; gap:8px; }}
    .chip {{ border:1px solid var(--line); border-radius:999px; padding:7px 10px; background:transparent; color:var(--text); cursor:pointer; }}
    .chip.active, .chip:hover {{ border-color:var(--accent); color:var(--accent); }}
    .chip span {{ color:var(--muted); margin-left:4px; }}
    .link {{ padding:17px; margin-bottom:12px; }}
    .link h2 {{ margin:0 0 7px; font-size:1.06rem; line-height:1.35; }}
    .link a {{ color:var(--accent); text-decoration:none; }}
    .link a:hover {{ text-decoration:underline; }}
    .meta {{ color:var(--muted); font-size:.9rem; display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }}
    .desc {{ color:var(--muted); margin:8px 0 0; }}
    .tag {{ color:var(--accent); cursor:pointer; }}
    .empty {{ text-align:center; color:var(--muted); padding:48px; border:1px dashed var(--line); border-radius:18px; }}
    .section-title {{ margin:18px 0 10px; font-size:.82rem; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; }}
    @media (max-width: 820px) {{ main {{ grid-template-columns:1fr; }} aside {{ position:static; }} .toolbar {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
<header>
  <h1>Linkbook</h1>
  <div class="sub">{len(links)} saved links · generated {escape(generated)}</div>
</header>
<main>
  <aside>
    <div class="stats">
      <div class="stat"><b>{len(links)}</b><span>links</span></div>
      <div class="stat"><b>{len(tags)}</b><span>tags</span></div>
      <div class="stat"><b>{len(categories)}</b><span>categories</span></div>
    </div>
    <button class="chip active" id="clearFilters">All links</button>
    <div class="section-title">Tags</div>
    <div class="chips">{tag_buttons}</div>
  </aside>
  <section>
    <div class="toolbar">
      <input id="search" placeholder="Search title, description, URL, tag…" autocomplete="off">
      <select id="category"><option value="">All categories</option>{category_options}</select>
      <select id="month"><option value="">All dates</option>{month_options}</select>
    </div>
    <div class="sub" id="summary"></div>
    <div id="links"></div>
  </section>
</main>
<script id="link-data" type="application/json">{links_json}</script>
<script>
const LINKS = JSON.parse(document.getElementById('link-data').textContent);
const state = {{ q: '', tag: '', category: '', month: '' }};
const els = {{
  search: document.getElementById('search'),
  category: document.getElementById('category'),
  month: document.getElementById('month'),
  list: document.getElementById('links'),
  summary: document.getElementById('summary'),
  clear: document.getElementById('clearFilters')
}};
function esc(s) {{ return String(s || '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])); }}
function matches(link) {{
  const haystack = [link.title, link.description, link.url, link.domain, link.category, ...(link.tags || [])].join(' ').toLowerCase();
  return (!state.q || haystack.includes(state.q)) &&
    (!state.tag || (link.tags || []).includes(state.tag)) &&
    (!state.category || link.category === state.category) &&
    (!state.month || link.saved_month === state.month);
}}
function render() {{
  const filtered = LINKS.filter(matches).sort((a,b) => (b.saved_at || '').localeCompare(a.saved_at || ''));
  els.summary.textContent = `${{filtered.length}} of ${{LINKS.length}} links${{state.tag ? ' tagged #' + state.tag : ''}}`;
  els.list.innerHTML = filtered.length ? filtered.map(link => `
    <article class="link">
      <h2><a href="${{esc(link.url)}}" target="_blank" rel="noreferrer">${{esc(link.title)}}</a></h2>
      ${{link.description ? `<p class="desc">${{esc(link.description)}}</p>` : ''}}
      <div class="meta">
        <span>${{esc(link.saved_date || 'undated')}}</span>
        <span>·</span><span>${{esc(link.domain)}}</span>
        <span>·</span><span>${{esc(link.category)}}</span>
        ${{(link.tags || []).map(t => `<span class="tag" data-tag="${{esc(t)}}">#${{esc(t)}}</span>`).join(' ')}}
      </div>
    </article>`).join('') : '<div class="empty">No links match these filters.</div>';
  document.querySelectorAll('.chip[data-filter-type="tag"]').forEach(btn => btn.classList.toggle('active', btn.dataset.filterValue === state.tag));
  els.clear.classList.toggle('active', !state.q && !state.tag && !state.category && !state.month);
}}
els.search.addEventListener('input', e => {{ state.q = e.target.value.trim().toLowerCase(); render(); }});
els.category.addEventListener('change', e => {{ state.category = e.target.value; render(); }});
els.month.addEventListener('change', e => {{ state.month = e.target.value; render(); }});
document.addEventListener('click', e => {{
  const tag = e.target.closest('[data-filter-type="tag"], .tag[data-tag]');
  if (tag) {{ state.tag = tag.dataset.filterValue || tag.dataset.tag; render(); window.scrollTo({{top:0, behavior:'smooth'}}); }}
}});
els.clear.addEventListener('click', () => {{ state.q = state.tag = state.category = state.month = ''; els.search.value = els.category.value = els.month.value = ''; render(); }});
render();
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Linkbook static site")
    parser.add_argument("--links", type=Path, default=DEFAULT_LINKS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    with args.links.open("r", encoding="utf-8") as f:
        raw_links = json.load(f)
    links = [normalize_link(link) for link in raw_links]

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "index.html").write_text(render_index(links), encoding="utf-8")
    (args.out / "links.json").write_text(json.dumps(links, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ Generated {args.out / 'index.html'} with {len(links)} links")


if __name__ == "__main__":
    main()
