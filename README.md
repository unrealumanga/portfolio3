# portfolio3

Portfolio site for **Hethusha Umanga Seneviratne**, experiential designer, Dubai.

Live: <https://unrealumanga.github.io/portfolio3/>

A restyle of the existing portfolio in an airy, large-type, monochrome
direction referenced from [aircenter.space](https://aircenter.space/). All
content — 32 projects, their descriptions, their galleries and their order —
is carried over unchanged from `unrealumanga/portfolio`, which this repo does
not touch.

## Stack

Static HTML, CSS and one progressive-enhancement JS file. No framework, no
runtime dependencies, no npm. Two Python build scripts generate the output,
which is committed.

- **Type:** Onest (variable, self-hosted, latin + latin-ext subsets, 48 KB)
- **Palette:** `#fff` / `#000` / `#606060` body / `#f2f2f2` surfaces
- **Pages:** `index.html` plus 32 static pages at `work/<slug>/`

Project pages render and navigate fully with JavaScript disabled. JS adds only
sector filtering, the lightbox, and scroll reveal.

## Layout

```
data/projects.json     source of truth, copied verbatim from the origin repo
data/images.json       generated: derivative paths + intrinsic dimensions
scripts/build_images.py  source stills/video -> WebP + MP4 derivatives
scripts/build_site.py    data + templates -> index.html and work/*/
scripts/verify.py        content-parity and structural assertions
templates/             index.html, project.html ({{token}} placeholders)
assets/css             tokens, base, layout, components
assets/js/app.js       filter, lightbox, reveal
assets/img/<slug>/     generated derivatives
```

## Building

Requires Python 3 with Pillow, and ffmpeg for the one video asset. Sources are
read from `../portfolio-repo` and are never modified.

```sh
python3 scripts/build_images.py     # --force to regenerate everything
python3 scripts/build_site.py
python3 scripts/verify.py
python3 -m http.server 8899         # then open http://localhost:8899/
```

`build_images.py` is idempotent — a derivative newer than its source is
skipped, so re-runs are cheap.

## Image pipeline

356 referenced assets, 386 MB at source, **105 MB** after processing.

| Tier | Purpose |
|:--|:--|
| `-640.webp` | work-grid cards at 1x, mobile |
| `-1280.webp` | work-grid cards at 2x |
| `-1920.webp` | project gallery and lightbox |

One gallery item is a video (Saudi Tadawul CMF). It is re-encoded from 45 MB
h264 at ~7 Mbps to 10.6 MB at CRF 24 with `+faststart`, and a poster frame is
extracted. Resolution is unchanged at 1280×720.

Derivative filenames carry a hash of the source path: several source
filenames slugify identically (Beeah has both `18. Majilis Area_upscale01.jpg`
and `18.-Majilis-Area_upscale01.jpg`) and would otherwise collide.

## Design rules

Built against `OBNOTES/llm-guideline-01-websites.md`. Notable points:

- The reference site uses `#8d8d8d` for body copy — 3.03:1 on white, which
  fails WCAG 2.2 SC 1.4.3. Body copy here is `#606060` (5.92:1).
- Every `<img>` and `<video>` carries explicit `width`/`height` from
  `images.json`, so nothing shifts on load.
- The hero is sized so the stats rule and the top of the figures are cut by the
  fold on a 900 px viewport — the page cannot read as complete.
- The first gallery image on each project page is preloaded as the LCP element;
  everything below is lazy.
- Filter state is conveyed by fill inversion plus `aria-pressed`, never by
  colour alone.

`scripts/verify.py` asserts content parity against `projects.json` and the
structural rules above. It runs 1043 checks.

## Known data gap

`JETEX-AERO-2026` has an empty `description` and `client` in the source data.
Per the content-parity decision this is carried over as-is: the page renders
title, sectors and gallery, and omits those blocks rather than emitting empty
elements.

## Relationship to the existing site

`unrealumanga/portfolio` and its published site are untouched. This repo reads
from `../portfolio-repo` at build time only. Nothing here writes to, commits
to, or deploys over it.
