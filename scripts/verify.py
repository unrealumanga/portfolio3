#!/usr/bin/env python3
"""Assert that the generated site matches the live portfolio's content model.

Parity is measured against data/site.json, which is extracted directly from the
deployed site's index.html. Exits non-zero on any failure.
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path("/workspace/portfolio/index.html")

failures = []
checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        failures.append(message)


site = json.loads((ROOT / "data" / "site.json").read_text())
images = json.loads((ROOT / "data" / "images.json").read_text())
index_html = (ROOT / "index.html").read_text()

featured, rows, galleries = site["featured"], site["index"], site["galleries"]

# --- Shape matches the live site ---
ADDED = {"dxb-terminal-c", "qiddiya-3-events"}  # new projects (featured: appended at end)
REPLACED = {"marina", "humain", "aldar"}  # galleries swapped for new selections
NEW = len(ADDED)  # projects added after the live-site extract (scripts/add_project.py)
check(len(featured) == 24 + NEW, f"expected {24 + NEW} featured cards, got {len(featured)}")
check(len(rows) == 36 + NEW, f"expected 36 index rows, got {len(rows)}")
check(len(galleries) == 36 + NEW, f"expected 36 galleries, got {len(galleries)}")
check(
    sum(len(g["images"]) for k, g in galleries.items() if k not in ADDED | REPLACED) == 170 - 8 - 12,  # live total minus marina (4), humain (4) and aldar (12), which were replaced
    "expected 170 gallery images in total",
)
check(len(site["sectors"]) == 5, "expected 5 sectors")

# --- Every index row resolves to a gallery ---
for row in rows:
    check(row["key"] in galleries, f"index row {row['no']} has no gallery")

# --- Featured order and wide/narrow rhythm match the source exactly ---
source = SOURCE.read_text()
grid = source[
    source.find('<div class="work-grid">') : source.find(
        "</div></section>", source.find('<div class="work-grid">')
    )
]
src_order = [k for k in re.findall(r"openLightbox\('([^']+)'\)", grid) if k in galleries]  # live site may be ahead of portfolio3
src_spans = [sp for sp, k in zip(re.findall(r'<button class="card (\w+)"', grid), re.findall(r"openLightbox\('([^']+)'\)", grid)) if k in galleries]
check([c["key"] for c in featured if c["key"] not in ADDED] == src_order, "featured order differs from source")
check([c["span"] for c in featured if c["key"] not in ADDED] == src_spans, "wide/narrow rhythm differs")

# --- Index order matches the source ---
index_block = source[source.find('id="index"') : source.find("</section>", source.find('id="index"'))]
src_index = [k for k in re.findall(r'<button class="index-row" onclick="openLightbox\(\'([^\']+)\'\)"', index_block) if k in galleries]
check([r["key"] for r in rows if r["key"] not in ADDED] == src_index, "index order differs from source")

# --- Index page ---
check("{{" not in index_html, "unsubstituted token in index.html")
check(index_html.count("<h1") == 1, "index.html must have exactly one h1 (W09)")
for landmark in ("<header", "<nav", "<main", "<footer"):
    check(landmark in index_html, f"index.html missing landmark {landmark} (W09)")

card_hrefs = re.findall(r'<a class="card card--\w+" href="work/([^/]+)/"', index_html)
check(card_hrefs == [c["key"] for c in featured], "rendered card order is wrong")

row_hrefs = re.findall(r'<a class="index-row" href="work/([^/]+)/"', index_html)
check(row_hrefs == [r["key"] for r in rows], "rendered index-row order is wrong")

# Titles and sub-lines appear verbatim.
for card in featured:
    check(
        html.escape(card["title"], quote=True) in index_html,
        f"card title missing: {card['title']}",
    )
for row in rows:
    check(
        html.escape(row["title"], quote=True) in index_html,
        f"index title missing: {row['title']}",
    )

# --- Project pages ---
for i, row in enumerate(rows):
    page = ROOT / "work" / row["key"] / "index.html"
    check(page.exists(), f"missing page for {row['key']}")
    if not page.exists():
        continue
    text = page.read_text()
    gallery = galleries[row["key"]]

    check("{{" not in text, f"{row['key']}: unsubstituted token")
    check(text.count("<h1") == 1, f"{row['key']}: must have exactly one h1")
    check(
        html.escape(row["title"], quote=True) in text,
        f"{row['key']}: title not present verbatim",
    )

    n_items = text.count('class="gallery-item"')
    check(
        n_items == len(gallery["images"]),
        f"{row['key']}: {n_items} gallery items, expected {len(gallery['images'])}",
    )

    # Gallery order matches the source array.
    rendered = re.findall(r'data-full="\.\./\.\./([^"]+)"', text)
    expected = []
    for image in gallery["images"]:
        entry = images.get(image["src"], {})
        tier = entry.get("1600") or entry.get("640")
        if tier:
            expected.append(tier["src"])
    check(rendered == expected, f"{row['key']}: gallery order does not match source")

    # Every caption carried through.
    for image in gallery["images"]:
        if image.get("cap"):
            check(
                html.escape(image["cap"], quote=True) in text,
                f"{row['key']}: caption missing: {image['cap']}",
            )

# --- W05: every img carries explicit width and height ---
pages = [ROOT / "index.html"] + sorted(ROOT.glob("work/*/index.html"))
for page in pages:
    text = page.read_text()
    for tag in re.findall(r"<img\b[^>]*>", text):
        if 'id="lightbox-img"' in tag:
            continue  # sized at runtime inside a fixed, contained stage
        check(
            'width="' in tag and 'height="' in tag,
            f"{page.relative_to(ROOT)}: <img> without width/height (W05)",
        )
        check('alt="' in tag, f"{page.relative_to(ROOT)}: <img> without alt")

# --- Referenced assets exist ---
missing = set()
for page in pages:
    base = page.parent
    text = page.read_text()
    for ref in re.findall(r'(?:src|href)="((?:\.\./)*assets/[^"]+)"', text):
        if not (base / ref).resolve().exists():
            missing.add(ref)
    for ref in re.findall(r'srcset="([^"]+)"', text):
        for part in ref.split(","):
            path = part.strip().split(" ")[0]
            if path and not (base / path).resolve().exists():
                missing.add(path)
check(not missing, f"{len(missing)} assets missing: {sorted(missing)[:4]}")

# --- Internal links resolve ---
broken = set()
for page in pages:
    base = page.parent
    for href in re.findall(
        r'href="((?:\.\./)*(?:work|index\.html)[^"#]*)"', page.read_text()
    ):
        target = (base / href).resolve()
        if target.is_dir():
            target = target / "index.html"
        if not target.exists():
            broken.add(f"{page.relative_to(ROOT)} -> {href}")
check(not broken, f"broken internal links: {sorted(broken)[:4]}")

print(f"{checks - len(failures)}/{checks} checks passed")
for failure in failures:
    print(f"  FAIL {failure}")
raise SystemExit(1 if failures else 0)
