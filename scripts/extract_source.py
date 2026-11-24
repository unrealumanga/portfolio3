#!/usr/bin/env python3
"""Extract the live portfolio's content into data/site.json.

The deployed site at unrealumanga.github.io/portfolio/ is a single
self-contained index.html with its data inlined. That file -- byte-identical to
/workspace/portfolio/index.html -- is the authority for project
naming, ordering, grouping and gallery contents.

Read-only: this never writes to the source tree.
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path("/workspace/portfolio/index.html")


def text(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def split_sub(sub):
    """'NEOM · Pavilion · 2024' -> ('NEOM', 'Pavilion', '2024')"""
    parts = [p.strip() for p in sub.split("·")]
    while len(parts) < 3:
        parts.append("")
    return parts[0], parts[1], parts[2]


def main():
    source = SOURCE.read_text()

    # --- Featured work grid: order and wide/narrow rhythm both matter ---
    grid_start = source.find('<div class="work-grid">')
    grid_end = source.find("</div></section>", grid_start)
    grid = source[grid_start:grid_end]

    featured = []
    for block in re.split(r'(?=<button class="card)', grid):
        if not block.startswith('<button class="card'):
            continue
        span = re.search(r'class="card (\w+)"', block)
        key = re.search(r"openLightbox\('([^']+)'\)", block)
        kv = re.search(r'<img src="([^"]+)"', block)
        title = re.search(r"<h3>(.*?)</h3>", block, re.S)
        sub = re.search(r'<div class="sub">(.*?)</div>', block, re.S)
        client, kind, year = split_sub(text(sub.group(1)) if sub else "")
        featured.append(
            {
                "key": key.group(1),
                "span": span.group(1),
                "title": text(title.group(1)),
                "client": client,
                "type": kind,
                "year": year,
                "kv": kv.group(1),
            }
        )

    # --- Galleries: name plus per-image captions ---
    galleries = json.loads(
        re.search(r"const GALLERIES = (\{.*?\});\n", source, re.S).group(1)
    )

    # --- Project index: the complete 36-project record ---
    index_start = source.find('id="index"')
    index_block = source[index_start : source.find("</section>", index_start)]
    # Rows are <button class="index-row" onclick="openLightbox('<key>')"> with
    # the client nested inside the name span.
    rows = []
    for match in re.finditer(
        r'<button class="index-row" onclick="openLightbox\(\'([^\']+)\'\)">(.*?)</button>',
        index_block,
        re.S,
    ):
        key, body = match.group(1), match.group(2)
        no = re.search(r'<span class="idx-no">(.*?)</span>', body, re.S)
        name = re.search(r'<span class="idx-name">(.*?)</span>\s*<span class="idx-cat">', body, re.S)
        client = re.search(r'<span class="cl">(.*?)</span>', body, re.S)
        cat = re.search(r'<span class="idx-cat">(.*?)</span>', body, re.S)
        year = re.search(r'<span class="idx-year">(.*?)</span>', body, re.S)
        title = text(name.group(1)) if name else ""
        client_text = text(client.group(1)) if client else ""
        if client_text and title.endswith(client_text):
            title = title[: -len(client_text)].strip()
        rows.append(
            {
                "no": text(no.group(1)) if no else "",
                "title": title,
                "client": client_text,
                "type": text(cat.group(1)) if cat else "",
                "year": text(year.group(1)) if year else "",
                "key": key,
            }
        )

    # --- Sectors ---
    sectors_start = source.find('id="sectors"')
    sectors_block = source[sectors_start : source.find("</section>", sectors_start)]
    sectors = [
        {"name": text(a), "count": text(b)}
        for a, b in re.findall(
            r"<div[^>]*>([^<]+)</div>\s*<div[^>]*>(\d+\s+projects?)</div>",
            sectors_block,
            re.S,
        )
    ]

    site = {
        "featured": featured,
        "index": rows,
        "galleries": galleries,
        "sectors": sectors,
    }
    (ROOT / "data" / "site.json").write_text(json.dumps(site, indent=1) + "\n")

    linked = sum(1 for r in rows if r["key"])
    print(f"featured cards : {len(featured)}")
    print(f"index rows     : {len(rows)} ({linked} linked to a gallery)")
    print(f"galleries      : {len(galleries)}")
    print(f"gallery images : {sum(len(g['images']) for g in galleries.values())}")
    print(f"sectors        : {len(sectors)}")

    unlinked = [r["title"] for r in rows if not r["key"]]
    if unlinked:
        print(f"! index rows with no gallery: {unlinked}")
    orphan = set(galleries) - {r["key"] for r in rows}
    if orphan:
        print(f"! galleries not in the index: {sorted(orphan)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
