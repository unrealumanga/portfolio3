# portfolio3

Portfolio site for **Hethusha Umanga Seneviratne**, experiential designer, Dubai.

Live: <https://unrealumanga.github.io/portfolio3/>

A restyle of the existing portfolio in an airy, large-type, monochrome
direction referenced from [aircenter.space](https://aircenter.space/). All
content — 24 featured projects in their curated order, the full 36-project
index, every gallery and every image caption — is carried over unchanged from
the deployed `unrealumanga/portfolio`, which this repo does not touch.

**Content authority.** The live site is a single self-contained `index.html`
with its data inlined. `/home/mnm/AI_Lab/Workspace/portfolio/index.html` is
byte-identical to what is deployed and is the source of truth.
`scripts/extract_source.py` parses it into `data/site.json`. Note that the
sibling `portfolio-repo/` checkout is an *abandoned earlier redesign* with
different project names, ordering and imagery — it is not the live site and
must not be used as a source.

## Stack

Static HTML, CSS and one progressive-enhancement JS file. No framework, no
runtime dependencies, no npm. Two Python build scripts generate the output,
which is committed.

- **Type:** Onest (variable, self-hosted, latin + latin-ext subsets, 48 KB)
- **Palette:** `#fff` / `#000` / `#606060` body / `#f2f2f2` surfaces
- **Pages:** `index.html` plus 36 static pages at `work/<key>/`

Project pages render and navigate fully with JavaScript disabled. JS adds only
the lightbox and scroll reveal.

## Layout

```
data/site.json         extracted from the live site: featured order, index,
                       galleries with per-image captions, sectors
data/images.json       generated: derivative paths + intrinsic dimensions
scripts/extract_source.py  live index.html -> data/site.json
scripts/build_images.py    source stills -> WebP derivatives
scripts/build_site.py    data + templates -> index.html and work/*/
scripts/verify.py        content-parity and structural assertions
templates/             index.html, project.html ({{token}} placeholders)
assets/css             tokens, base, layout, components
assets/js/app.js       lightbox, reveal
assets/img/             generated derivatives
```

## Building

Requires Python 3 with Pillow. Sources are read from `../portfolio` and are
never modified.

```sh
python3 scripts/extract_source.py   # re-read the live site's content
python3 scripts/build_images.py     # --force to regenerate everything
python3 scripts/build_site.py
python3 scripts/verify.py
python3 -m http.server 8899         # then open http://localhost:8899/
```

`build_images.py` is idempotent — a derivative newer than its source is
skipped, so re-runs are cheap.

## Content model

| Piece | Count |
|:--|:--|
| Featured cards (curated order, wide/narrow rhythm) | 24 |
| Project index rows | 36 |
| Galleries | 36 |
| Gallery images, with captions | 170 |
| Sectors | 5 |

The featured grid, the index and prev/next each keep their own deliberate
order, inherited from the live site rather than derived. Project pages are
generated for all 36 and paged in index order, since every project appears
there while only 24 are featured.

## Image pipeline

171 referenced assets, 19.5 MB at source, **21 MB** after processing (WebP at
two widths). Sources are already web-sized at 1100×614 and 1600×900.

| Tier | Purpose |
|:--|:--|
| `-640.webp` | narrow cards, mobile |
| `-1600.webp` | wide cards, gallery, lightbox |

Neither tier upscales. Derivative filenames carry a hash of the source path to
keep distinct sources on distinct outputs.

## Design rules

Built against `OBNOTES/llm-guideline-01-websites.md`. Notable points:

- The reference site uses `#8d8d8d` for body copy — 3.03:1 on white, which
  fails WCAG 2.2 SC 1.4.3. Body copy here is `#606060` (5.92:1).
- Every `<img>` carries explicit `width`/`height` from `images.json`, so
  nothing shifts on load.
- The hero is sized so the figures rule is cut by the fold on a 900 px
  viewport — the page cannot read as complete.
- The first gallery image on each project page is preloaded as the LCP element;
  everything below is lazy.

`scripts/verify.py` asserts content parity against `data/site.json` *and*
re-parses the live source to confirm the featured order, the wide/narrow
rhythm and the index order still match. It runs 890 checks.

## Relationship to the existing site

`unrealumanga/portfolio` and its published site are untouched. This repo reads
`../portfolio/index.html` and `../portfolio/img/` at build time only. Nothing
here writes to, commits to, or deploys over it.
