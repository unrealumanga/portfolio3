#!/usr/bin/env python3
"""Render index.html and work/<slug>/index.html from data + templates.

Templates are plain HTML with {{token}} placeholders. Every interpolated value
is HTML-escaped. Project pages are emitted in projects.json array order, so
prev/next follows the same sequence as the work index.
"""

import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"

CARD_SIZES = "(min-width: 1280px) 31vw, (min-width: 700px) 47vw, 92vw"
GALLERY_SIZES = "(min-width: 1720px) 1656px, 92vw"


def esc(value):
    return html.escape(str(value or ""), quote=True)


def fill(template, values):
    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def load():
    projects = json.loads((ROOT / "data" / "projects.json").read_text())
    images = json.loads((ROOT / "data" / "images.json").read_text())
    return projects, images


def srcset(entry, widths):
    parts = []
    for width in widths:
        tier = entry.get(str(width))
        if tier:
            parts.append(f"{tier['src']} {tier['w']}w")
    return ", ".join(parts)


def largest(entry):
    """Widest still tier available for an image entry."""
    tiers = [entry[k] for k in ("1920", "1280", "640") if k in entry]
    return tiers[0] if tiers else None


def render_card(project, index, images, prefix=""):
    thumb = project.get("thumbnail")
    entry = images.get(thumb) or {}
    tier = entry.get("640") or largest(entry)
    if not tier:
        return ""

    sectors = " · ".join(project.get("sectors") or [])
    gallery_n = len(project.get("gallery") or [])
    # W30: the first three cards are the plausible LCP candidates on the index.
    eager = index < 3
    loading = 'loading="eager" fetchpriority="high"' if eager else 'loading="lazy"'

    return f"""<a class="card" href="{prefix}work/{esc(project['slug'])}/"
   data-sectors="{esc('|'.join(project.get('sectors') or []))}">
  <div class="card-frame">
    <span class="card-index">{index + 1:02d}</span>
    <img src="{esc(tier['src'])}"
         srcset="{esc(srcset(entry, (640, 1280)))}"
         sizes="{CARD_SIZES}"
         width="{tier['w']}" height="{tier['h']}"
         alt="{esc(project.get('title'))} — {esc(project.get('client') or 'project')} visual"
         {loading} decoding="async" />
  </div>
  <div class="card-body">
    <div>
      <div class="card-title">{esc(project.get('title'))}</div>
      <p class="micro card-client">{esc(project.get('client') or sectors)}</p>
    </div>
    <span class="micro card-count">{gallery_n}</span>
  </div>
</a>"""


def render_gallery(project, images):
    out = []
    for i, ref in enumerate(project.get("gallery") or []):
        entry = images.get(ref)
        if not entry:
            continue
        title = esc(project.get("title"))

        if entry.get("type") == "video":
            poster = entry["poster"]
            out.append(
                f"""<video class="gallery-item" controls preload="none"
       poster="../../{esc(poster['src'])}"
       width="{entry['w']}" height="{entry['h']}">
  <source src="../../{esc(entry['video'])}" type="video/mp4" />
  Your browser does not support embedded video.
</video>"""
            )
            continue

        tier = entry.get("1920") or largest(entry)
        # W30: first image is the LCP element -- eager, high priority.
        loading = (
            'loading="eager" fetchpriority="high"' if i == 0 else 'loading="lazy"'
        )
        full = tier["src"]
        out.append(
            f"""<button class="gallery-item" type="button"
        data-full="../../{esc(full)}" data-index="{i}"
        aria-label="Open image {i + 1} full size">
  <img src="../../{esc(tier['src'])}"
       srcset="{esc(', '.join(f'../../{t}' for t in srcset(entry, (640, 1280, 1920)).split(', ')))}"
       sizes="{GALLERY_SIZES}"
       width="{tier['w']}" height="{tier['h']}"
       alt="{title} — view {i + 1}"
       {loading} decoding="async" />
</button>"""
        )
    return "\n".join(out)


def render_index(projects, images):
    template = (TEMPLATES / "index.html").read_text()

    sector_counts = {}
    for project in projects:
        for sector in project.get("sectors") or []:
            sector_counts[sector] = sector_counts.get(sector, 0) + 1
    ordered_sectors = sorted(sector_counts.items(), key=lambda kv: (-kv[1], kv[0]))

    filters = [
        '<button class="pill" type="button" data-sector="__all__" '
        f'aria-pressed="true">All<span class="count">{len(projects)}</span></button>'
    ]
    for sector, count in ordered_sectors:
        filters.append(
            '<button class="pill" type="button" '
            f'data-sector="{esc(sector)}" aria-pressed="false">{esc(sector)}'
            f'<span class="count">{count}</span></button>'
        )

    rows = [
        f'<li class="sector-row"><span class="sector-row-name">{esc(s)}</span>'
        f'<span class="micro">{c} project{"s" if c != 1 else ""}</span></li>'
        for s, c in ordered_sectors
    ]

    cards = [render_card(p, i, images) for i, p in enumerate(projects)]

    first_thumb = images.get(projects[0].get("thumbnail"), {})
    og_tier = first_thumb.get("1280") or largest(first_thumb) or {"src": ""}

    return fill(
        template,
        {
            "stat_projects": str(len(projects)),
            "stat_sectors": str(len(sector_counts)),
            "filters": "\n          ".join(filters),
            "work_grid": "\n          ".join(cards),
            "sector_rows": "\n            ".join(rows),
            "og_image": esc(og_tier["src"]),
        },
    )


def render_project(project, index, projects, images):
    template = (TEMPLATES / "project.html").read_text()
    total = len(projects)
    prev_p = projects[index - 1] if index > 0 else None
    next_p = projects[(index + 1) % total]

    prev_link = (
        f'<a class="icon-btn" href="../{esc(prev_p["slug"])}/" '
        f'aria-label="Previous project: {esc(prev_p["title"])}">&larr;</a>'
        if prev_p
        else '<span class="icon-btn" aria-disabled="true" aria-hidden="true">&larr;</span>'
    )
    next_link = (
        f'<a class="icon-btn" href="../{esc(next_p["slug"])}/" '
        f'aria-label="Next project: {esc(next_p["title"])}">&rarr;</a>'
    )

    meta_items = []
    if project.get("client"):
        meta_items.append(
            f'<div class="project-meta-item"><dt>Client</dt>'
            f'<dd>{esc(project["client"])}</dd></div>'
        )
    if project.get("year"):
        meta_items.append(
            f'<div class="project-meta-item"><dt>Year</dt>'
            f'<dd>{esc(project["year"])}</dd></div>'
        )
    gallery_n = len(project.get("gallery") or [])
    meta_items.append(
        f'<div class="project-meta-item"><dt>Visuals</dt><dd>{gallery_n}</dd></div>'
    )

    description = (project.get("description") or "").strip()
    description_block = (
        f'<p class="lead project-description">{esc(description)}</p>'
        if description
        else ""
    )

    sectors = " · ".join(project.get("sectors") or []) or "Project"
    meta_description = description[:180] if description else (
        f'{project.get("title")} — spatial design project by '
        f"Hethusha Umanga Seneviratne."
    )

    # LCP preload for the first gallery still.
    lcp_preload = ""
    og_image = ""
    for ref in project.get("gallery") or []:
        entry = images.get(ref)
        if entry and entry.get("type") != "video":
            tier = entry.get("1920") or largest(entry)
            lcp_preload = (
                f'<link rel="preload" as="image" href="../../{esc(tier["src"])}" '
                f'imagesrcset="{esc(", ".join(f"../../{t}" for t in srcset(entry, (640, 1280, 1920)).split(", ")))}" '
                f'imagesizes="{GALLERY_SIZES}" fetchpriority="high" />'
            )
            og_image = esc((entry.get("1280") or tier)["src"])
            break

    return fill(
        template,
        {
            "title": esc(project.get("title")),
            "slug": esc(project.get("slug")),
            "sectors": esc(sectors),
            "meta_items": "\n            ".join(meta_items),
            "description_block": description_block,
            "meta_description": esc(meta_description),
            "gallery": render_gallery(project, images),
            "position": f"{index + 1:02d}",
            "total": f"{total:02d}",
            "prev_link": prev_link,
            "next_link": next_link,
            "next_href": f'../{esc(next_p["slug"])}/',
            "next_title": esc(next_p["title"]),
            "lcp_preload": lcp_preload,
            "og_image": og_image,
        },
    )


def main():
    projects, images = load()

    (ROOT / "index.html").write_text(render_index(projects, images))
    print(f"index.html          ({len(projects)} cards)")

    work_dir = ROOT / "work"
    if work_dir.exists():
        shutil.rmtree(work_dir)

    for i, project in enumerate(projects):
        out_dir = work_dir / project["slug"]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(render_project(project, i, projects, images))

    print(f"work/*/index.html   ({len(projects)} pages)")

    leftover = [t for t in ("{{", "}}") if t in (ROOT / "index.html").read_text()]
    if leftover:
        print("! unsubstituted tokens remain in index.html")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
