#!/usr/bin/env python3
"""Render index.html and work/<key>/index.html from data/site.json.

Ordering is inherited from the live site and is deliberate, not derived:
 - the featured grid keeps the curated 24-card order and its wide/narrow rhythm
 - the project index keeps its own 36-row order (alphabetical by client)
 - prev/next on project pages follows the index order, since every project
   appears there while only 24 are featured
"""

import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"

WIDE_SIZES = "(min-width: 900px) 56vw, 92vw"
NARROW_SIZES = "(min-width: 900px) 37vw, 92vw"
GALLERY_SIZES = "(min-width: 1720px) 1656px, 92vw"
HERO_SIZES = "92vw"


def esc(value):
    return html.escape(str(value or ""), quote=True)


def fill(template, values):
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def srcset(entry, prefix=""):
    parts = []
    for width in ("640", "1600"):
        tier = entry.get(width)
        if tier:
            parts.append(f"{prefix}{tier['src']} {tier['w']}w")
    return ", ".join(parts)


def widest(entry):
    return entry.get("1600") or entry.get("640")


def sub_line(item):
    bits = [item.get("client"), item.get("type"), item.get("year")]
    return " · ".join(b for b in bits if b)


def render_card(card, position, images):
    entry = images.get(card["kv"])
    if not entry:
        return ""
    tier = entry.get("1600") if card["span"] == "wide" else entry.get("640")
    tier = tier or widest(entry)
    sizes = WIDE_SIZES if card["span"] == "wide" else NARROW_SIZES
    # W30: the first two cards are the LCP candidates in the grid.
    loading = (
        'loading="eager" fetchpriority="high"' if position < 2 else 'loading="lazy"'
    )
    return f"""<a class="card card--{card['span']}" href="work/{esc(card['key'])}/">
  <div class="card-frame">
    <img src="{esc(tier['src'])}"
         srcset="{esc(srcset(entry))}" sizes="{sizes}"
         width="{tier['w']}" height="{tier['h']}"
         alt="{esc(card['title'])}"
         {loading} decoding="async" />
  </div>
  <div class="card-meta">
    <span class="micro card-no">{position + 1:02d}</span>
    <div>
      <h3 class="card-title">{esc(card['title'])}</h3>
      <p class="micro card-sub">{esc(sub_line(card))}</p>
    </div>
  </div>
</a>"""


def render_index_row(row):
    return f"""<a class="index-row" href="work/{esc(row['key'])}/">
  <span class="micro idx-no">{esc(row['no'])}</span>
  <span class="idx-name">{esc(row['title'])}<span class="micro cl">{esc(row['client'])}</span></span>
  <span class="micro idx-cat">{esc(row['type'])}</span>
  <span class="micro idx-year">{esc(row['year'])}</span>
</a>"""


def render_gallery(gallery, images):
    out = []
    for i, image in enumerate(gallery["images"]):
        entry = images.get(image["src"])
        if not entry:
            continue
        tier = widest(entry)
        caption = image.get("cap") or ""
        alt = f"{gallery['name']} — {caption}" if caption else gallery["name"]
        loading = (
            'loading="eager" fetchpriority="high"' if i == 0 else 'loading="lazy"'
        )
        cap_html = (
            f'<figcaption class="micro gallery-cap">{esc(caption)}</figcaption>'
            if caption
            else ""
        )
        out.append(
            f"""<figure class="gallery-figure">
  <button class="gallery-item" type="button"
          data-full="../../{esc(tier['src'])}" data-cap="{esc(caption)}"
          aria-label="Open image {i + 1} of {len(gallery['images'])} full size">
    <img src="../../{esc(tier['src'])}"
         srcset="{esc(srcset(entry, '../../'))}" sizes="{GALLERY_SIZES}"
         width="{tier['w']}" height="{tier['h']}"
         alt="{esc(alt)}"
         {loading} decoding="async" />
  </button>
  {cap_html}
</figure>"""
        )
    return "\n".join(out)


def render_index(site, images):
    template = (TEMPLATES / "index.html").read_text()

    cards = [render_card(c, i, images) for i, c in enumerate(site["featured"])]
    rows = [render_index_row(r) for r in site["index"]]
    sectors = [
        f'<li class="sector-row"><span class="sector-row-name">{esc(s["name"])}</span>'
        f'<span class="micro">{esc(s["count"])}</span></li>'
        for s in site["sectors"]
    ]

    hero_entry = images.get("img/hero.jpg")
    hero_html, lcp_preload, og_image = "", "", ""
    if hero_entry:
        tier = widest(hero_entry)
        hero_html = (
            f'<img src="{esc(tier["src"])}" srcset="{esc(srcset(hero_entry))}" '
            f'sizes="{HERO_SIZES}" width="{tier["w"]}" height="{tier["h"]}" '
            f'alt="Trojena Mobile Pavilion, NEOM" '
            f'loading="eager" fetchpriority="high" decoding="async" />'
        )
        lcp_preload = (
            f'<link rel="preload" as="image" href="{esc(tier["src"])}" '
            f'imagesrcset="{esc(srcset(hero_entry))}" imagesizes="{HERO_SIZES}" '
            f'fetchpriority="high" />'
        )
        og_image = esc(tier["src"])

    return fill(
        template,
        {
            "work_grid": "\n          ".join(cards),
            "index_rows": "\n          ".join(rows),
            "index_count": str(len(site["index"])),
            "sector_rows": "\n          ".join(sectors),
            "hero_image": hero_html,
            "lcp_preload": lcp_preload,
            "og_image": og_image,
        },
    )


def render_project(row, position, order, site, images):
    template = (TEMPLATES / "project.html").read_text()
    gallery = site["galleries"][row["key"]]
    total = len(order)
    prev_row = order[position - 1] if position > 0 else None
    next_row = order[(position + 1) % total]

    prev_link = (
        f'<a class="icon-btn" href="../{esc(prev_row["key"])}/" '
        f'aria-label="Previous project: {esc(prev_row["title"])}">&larr;</a>'
        if prev_row
        else '<span class="icon-btn" aria-disabled="true" aria-hidden="true">&larr;</span>'
    )
    next_link = (
        f'<a class="icon-btn" href="../{esc(next_row["key"])}/" '
        f'aria-label="Next project: {esc(next_row["title"])}">&rarr;</a>'
    )

    meta_items = []
    for label, value in (
        ("Client", row.get("client")),
        ("Sector", row.get("type")),
        ("Year", row.get("year")),
    ):
        if value:
            meta_items.append(
                f'<div class="project-meta-item"><dt>{label}</dt>'
                f"<dd>{esc(value)}</dd></div>"
            )
    meta_items.append(
        f'<div class="project-meta-item"><dt>Visuals</dt>'
        f'<dd>{len(gallery["images"])}</dd></div>'
    )

    lcp_preload, og_image = "", ""
    if gallery["images"]:
        entry = images.get(gallery["images"][0]["src"])
        if entry:
            tier = widest(entry)
            lcp_preload = (
                f'<link rel="preload" as="image" href="../../{esc(tier["src"])}" '
                f'imagesrcset="{esc(srcset(entry, "../../"))}" '
                f'imagesizes="{GALLERY_SIZES}" fetchpriority="high" />'
            )
            og_image = esc(tier["src"])

    return fill(
        template,
        {
            "title": esc(row["title"]),
            "key": esc(row["key"]),
            "sub": esc(sub_line(row)),
            "meta_items": "\n            ".join(meta_items),
            "meta_description": esc(
                f"{row['title']} — {sub_line(row)}. Spatial design by "
                f"Hethusha Umanga Seneviratne."
            ),
            "gallery": render_gallery(gallery, images),
            "position": f"{position + 1:02d}",
            "total": f"{total:02d}",
            "prev_link": prev_link,
            "next_link": next_link,
            "next_href": f'../{esc(next_row["key"])}/',
            "next_title": esc(next_row["title"]),
            "next_sub": esc(sub_line(next_row)),
            "lcp_preload": lcp_preload,
            "og_image": og_image,
        },
    )


def main():
    site = json.loads((ROOT / "data" / "site.json").read_text())
    images = json.loads((ROOT / "data" / "images.json").read_text())

    (ROOT / "index.html").write_text(render_index(site, images))
    print(f"index.html          ({len(site['featured'])} cards, "
          f"{len(site['index'])} index rows)")

    work_dir = ROOT / "work"
    if work_dir.exists():
        shutil.rmtree(work_dir)

    order = site["index"]
    for i, row in enumerate(order):
        out_dir = work_dir / row["key"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(
            render_project(row, i, order, site, images)
        )
    print(f"work/*/index.html   ({len(order)} pages)")

    if "{{" in (ROOT / "index.html").read_text():
        print("! unsubstituted tokens remain in index.html")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
