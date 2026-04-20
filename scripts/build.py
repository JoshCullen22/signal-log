#!/usr/bin/env python3
"""Signal Log — static site generator.

Reads entries/*.md → writes public/*.html + public/index.html.
Also emits public/feed.json (JSON Feed 1.1) and public/entries.json (machine index).

Run: python3 scripts/build.py
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRIES_DIR = ROOT / "entries"
PUBLIC_DIR = ROOT / "docs"
SITE_URL = "https://joshcullensantos.github.io/signal-log"  # Josh changes after GH pages setup
SITE_TITLE = "Signal Log"
SITE_BYLINE = "Josh Cullen Santos"


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def parse_entry(path: Path) -> dict:
    text = path.read_text()
    m = FRONTMATTER_RE.match(text)
    meta: dict = {}
    body = text
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
        body = m.group(2)
    # Fallback from filename: YYYY-MM-DD-slug.md
    stem = path.stem
    if not meta.get("date") and len(stem) >= 10:
        meta["date"] = stem[:10]
    if not meta.get("slug"):
        meta["slug"] = stem[11:] if len(stem) > 10 else stem
    if not meta.get("title"):
        meta["title"] = meta.get("slug", path.stem).replace("-", " ").title()
    meta["hash"] = hashlib.sha256(text.encode()).hexdigest()
    meta["file"] = path.name
    meta["body"] = body
    return meta


def markdown_to_html(md: str) -> str:
    """Tiny markdown subset — headings, paragraphs, bold, italic, code, links, lists.
    We avoid pulling in a dependency; this is enough for a journal."""
    html_parts = []
    lines = md.splitlines()
    in_code = False
    in_list = False
    paragraph: list[str] = []

    def flush_para():
        nonlocal paragraph
        if paragraph:
            text = " ".join(paragraph).strip()
            if text:
                html_parts.append(f"<p>{inline(text)}</p>")
            paragraph = []

    def inline(t: str) -> str:
        t = html.escape(t)
        t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", t)
        t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
        return t

    for line in lines:
        if line.strip().startswith("```"):
            flush_para()
            if in_code:
                html_parts.append("</code></pre>")
                in_code = False
            else:
                html_parts.append("<pre><code>")
                in_code = True
            continue
        if in_code:
            html_parts.append(html.escape(line))
            continue
        if line.startswith("# "):
            flush_para()
            html_parts.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("## "):
            flush_para()
            html_parts.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("### "):
            flush_para()
            html_parts.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("- "):
            flush_para()
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{inline(line[2:])}</li>")
        elif not line.strip():
            if in_list:
                html_parts.append("</ul>")
                in_list = False
            flush_para()
        else:
            paragraph.append(line)
    if in_list:
        html_parts.append("</ul>")
    flush_para()
    return "\n".join(html_parts)


def git_commit_of(path: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(ROOT), "log", "-n", "1", "--pretty=format:%H %aI", str(path)],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        return out
    except Exception:
        return ""


def page_shell(title: str, body: str, entries: list[dict] | None = None) -> str:
    nav = ""
    if entries is not None:
        nav = '<nav class="entries">'
        for e in entries:
            nav += f'<a href="{e["slug"]}.html" class="entry-link"><span class="date">{e["date"]}</span> <span class="title">{html.escape(e["title"])}</span></a>'
        nav += "</nav>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} — {SITE_TITLE}</title>
  <meta name="author" content="{SITE_BYLINE}">
  <meta name="description" content="Tamper-evident public log of Josh Cullen Santos' original work. Cryptographically timestamped.">
  <link rel="icon" type="image/svg+xml" href="/signal-log/favicon.svg">
  <style>
    :root {{ --gold:#e8c070; --blood:#e89090; --ink:#0a0a0e; --bone:#ece9e2; --chrome:#8892a4; }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; }}
    body {{
      background: var(--ink); color: var(--bone);
      font-family: ui-serif, Georgia, 'Iowan Old Style', serif;
      line-height: 1.6; font-size: 17px;
    }}
    .wrap {{ max-width: 720px; margin: 0 auto; padding: 48px 24px 96px; }}
    header.site {{ border-bottom: 1px solid #2a2a32; padding-bottom: 20px; margin-bottom: 40px; }}
    header.site h1 {{ margin: 0; font-family: ui-monospace, 'SF Mono', monospace; font-size: 24px; letter-spacing: 2px; color: var(--gold); }}
    header.site .byline {{ color: var(--chrome); font-size: 13px; text-transform: uppercase; letter-spacing: 3px; margin-top: 4px; }}
    header.site .shield {{ color: var(--blood); font-size: 12px; margin-top: 16px; font-family: ui-monospace, 'SF Mono', monospace; }}
    article h1 {{ color: var(--gold); font-family: ui-monospace, 'SF Mono', monospace; font-size: 28px; margin-bottom: 8px; }}
    article .meta {{ color: var(--chrome); font-size: 13px; font-family: ui-monospace, 'SF Mono', monospace; margin-bottom: 32px; }}
    article .meta .hash {{ display: block; margin-top: 4px; font-size: 11px; color: #4a525f; word-break: break-all; }}
    article h2 {{ color: var(--gold); margin-top: 40px; font-family: ui-monospace, 'SF Mono', monospace; font-size: 18px; }}
    article h3 {{ color: var(--bone); font-family: ui-monospace, 'SF Mono', monospace; font-size: 15px; margin-top: 28px; }}
    article p {{ margin: 0 0 18px; }}
    article a {{ color: var(--gold); }}
    article code {{ background: #1a1a22; padding: 1px 6px; border-radius: 3px; font-size: 14px; color: var(--gold); }}
    article pre {{ background: #0f0f15; padding: 16px; border-left: 2px solid var(--gold); overflow-x: auto; }}
    article pre code {{ background: transparent; padding: 0; }}
    nav.entries {{ display: flex; flex-direction: column; gap: 10px; }}
    .entry-link {{ display: flex; gap: 20px; color: inherit; text-decoration: none; padding: 12px 0; border-bottom: 1px solid #1a1a22; transition: all .15s; }}
    .entry-link:hover {{ border-bottom-color: var(--gold); }}
    .entry-link .date {{ color: var(--chrome); font-family: ui-monospace, 'SF Mono', monospace; font-size: 13px; min-width: 100px; }}
    .entry-link .title {{ color: var(--bone); }}
    .entry-link:hover .title {{ color: var(--gold); }}
    footer {{ margin-top: 80px; padding-top: 20px; border-top: 1px solid #2a2a32; color: var(--chrome); font-size: 12px; font-family: ui-monospace, 'SF Mono', monospace; }}
    .back {{ color: var(--chrome); text-decoration: none; font-family: ui-monospace, 'SF Mono', monospace; font-size: 13px; }}
    .back:hover {{ color: var(--gold); }}
  </style>
</head>
<body>
<div class="wrap">
  <header class="site">
    <h1>◉ SIGNAL LOG</h1>
    <div class="byline">{SITE_BYLINE}</div>
    <div class="shield">🛡 Tamper-evident · SHA-chained · OpenTimestamps-anchored</div>
  </header>
  {body}
  <footer>
    <p><strong>All Rights Reserved © {SITE_BYLINE}, 2026.</strong> This log establishes authorship; content is not licensed for reuse.</p>
    <p>Verify any entry: <code>ots verify entries/&lt;file&gt;.md.ots</code>. Every commit is cryptographically chained to the one before.</p>
  </footer>
</div>
</body>
</html>"""


def main() -> None:
    PUBLIC_DIR.mkdir(exist_ok=True)
    # Favicon — same SIGNAL mark as the office
    fav = PUBLIC_DIR / "favicon.svg"
    fav.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="10" fill="#0a0a0e"/>'
        '<circle cx="32" cy="40" r="6" fill="none" stroke="#e8c070" stroke-width="2"/>'
        '<circle cx="32" cy="40" r="12" fill="none" stroke="#e8c070" stroke-width="1.5" opacity="0.7"/>'
        '<circle cx="32" cy="40" r="18" fill="none" stroke="#e8c070" stroke-width="1" opacity="0.4"/>'
        '<circle cx="32" cy="40" r="2.5" fill="#e8c070"/>'
        '<rect x="31" y="14" width="2" height="22" fill="#c8ccd4"/>'
        '<circle cx="32" cy="14" r="3" fill="#e89090"/>'
        "</svg>"
    )

    entries = []
    for md in sorted(ENTRIES_DIR.glob("*.md"), reverse=True):
        e = parse_entry(md)
        commit = git_commit_of(md)
        body_html = markdown_to_html(e["body"])
        article = (
            f'<a class="back" href="index.html">← all entries</a>'
            f'<article>'
            f'<h1>{html.escape(e["title"])}</h1>'
            f'<div class="meta">{e["date"]} · {SITE_BYLINE}'
        )
        if commit:
            sha, ts = commit.split(" ", 1) if " " in commit else (commit, "")
            article += f' · git {sha[:10]} · {ts}'
        article += (
            f'<span class="hash">sha256: {e["hash"]}</span>'
            f"</div>{body_html}</article>"
        )
        (PUBLIC_DIR / f'{e["slug"]}.html').write_text(page_shell(e["title"], article))
        entries.append(e)

    # Index
    index_body = "<h2 style='color: var(--chrome); font-family: ui-monospace, monospace; font-size: 14px; letter-spacing: 2px;'>ENTRIES</h2>"
    (PUBLIC_DIR / "index.html").write_text(page_shell("Index", index_body, entries))

    # JSON feed
    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": SITE_TITLE,
        "home_page_url": SITE_URL,
        "feed_url": f"{SITE_URL}/feed.json",
        "authors": [{"name": SITE_BYLINE}],
        "items": [
            {
                "id": f"{SITE_URL}/{e['slug']}.html",
                "url": f"{SITE_URL}/{e['slug']}.html",
                "title": e["title"],
                "date_published": e["date"] + "T00:00:00Z",
                "content_text": e["body"][:500],
                "_sha256": e["hash"],
            }
            for e in entries
        ],
    }
    (PUBLIC_DIR / "feed.json").write_text(json.dumps(feed, indent=2))
    print(f"built {len(entries)} entries → {PUBLIC_DIR}")


if __name__ == "__main__":
    main()
