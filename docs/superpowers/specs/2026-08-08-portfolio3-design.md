# portfolio3 — Design Spec

**Date:** 2026-08-08
**Status:** Approved
**Owner:** Hethusha Umanga Seneviratne

---

## 1. Purpose

Build a new, separately-hosted portfolio site for Hethusha Umanga Seneviratne,
restyled after the airy, large-type, monochrome aesthetic of
`https://aircenter.space/`.

The existing site at `https://unrealumanga.github.io/portfolio/` and its repo
`unrealumanga/portfolio` are **read-only sources**. This project must not
modify, commit to, or push to them.

## 2. Non-goals

- Changing any content: no new copy, no reordered projects, no re-curated galleries.
- Adding a CMS, framework, or client-side build toolchain.
- Migrating or deleting the existing site.

## 3. Constraints

| Constraint | Source |
|:--|:--|
| WCAG 2.2 AA conformance | `OBNOTES/llm-guideline-01-websites.md` §2, Tier 1 |
| LCP ≤ 2.5 s, INP ≤ 200 ms, CLS ≤ 0.1 | ibid. §5 |
| GitHub Pages published-site limit: 1 GB | GitHub Pages docs |
| Source images total 341 MB across 356 files | measured |
| No `sharp`; Pillow 12.1.1 available | measured |

## 4. Sources of truth

| Item | Path |
|:--|:--|
| Project data | `portfolio-repo/data/projects.json` (32 projects) |
| Gallery images | `portfolio-repo/projects/<slug>/…` (356 referenced files) |
| Site copy | `portfolio-repo/index.html` |
| Design reference | `https://aircenter.space/` |
| Design rules | `OBNOTES/llm-guideline-01-websites.md` |

`projects.json` is copied byte-for-byte. Verified: md5
`539ce2ef7e884b0761a1c6e808f015df`.

## 5. Deployment

- Repo: `unrealumanga/portfolio3`, public.
- Pages source: `main` branch, root.
- URL: `https://unrealumanga.github.io/portfolio3/`.
- Local working copy: `/home/mnm/AI_Lab/Workspace/portfolio3/`, fresh
  `git init`, no shared history with `unrealumanga/portfolio`.
- All asset references are relative, so the `/portfolio3/` path prefix needs no
  build-time configuration.

## 6. Architecture

Static site, no runtime framework. Two build scripts produce the deployable
tree; the output is committed.

```
portfolio3/
  data/projects.json        copied verbatim from portfolio-repo
  data/images.json          generated: derivative paths + intrinsic dimensions
  scripts/build_images.py   JPEG -> WebP derivatives
  scripts/build_site.py     data + templates -> HTML
  templates/*.html          index and project page templates
  assets/css/*.css          tokens, base, layout, components
  assets/js/app.js          sector filter + lightbox
  assets/fonts/*.woff2      self-hosted Onest
  assets/img/<slug>/*.webp  generated derivatives
  index.html                generated
  work/<slug>/index.html    generated, 32 pages
```

### 6.1 `build_images.py`

Reads `data/projects.json`. For every referenced thumbnail and gallery image,
emits two WebP derivatives into `assets/img/<slug>/`:

| Derivative | Width | Quality | Used by |
|:--|:--|:--|:--|
| `<name>-640.webp` | 640 px | 80 | work-grid cards |
| `<name>-1920.webp` | 1920 px | 78 | project gallery, lightbox |

Images narrower than a target width are not upscaled; the derivative is written
at the source width. Both derivatives' actual pixel dimensions are recorded in
`data/images.json`, keyed by the original relative path, so every `<img>` can
carry explicit `width` and `height`.

The script is idempotent: an existing derivative newer than its source is
skipped.

Estimated output: ~115 MB. The actual figure is measured after the first run
and recorded in the README.

### 6.2 `build_site.py`

Reads `data/projects.json` and `data/images.json`, renders:

- `index.html` — the one-page site.
- `work/<slug>/index.html` — one page per project, 32 total, iterated in
  `projects.json` array order so prev/next follows the same sequence as the
  work index.

Templates are plain HTML with `{{token}}` placeholders substituted in Python —
no template engine dependency. All interpolated values are HTML-escaped.

### 6.3 Page structure

**`index.html`** — single scroll:

1. Hero — h1, lead paragraph, primary CTA, stat row
2. Selected Work — sector filter pills + 32-card grid
3. Studio & Process — intro + three process steps
4. Capabilities — four cards
5. Sectors — sector list with counts + stat block
6. Contact — email, phone, location

**`work/<slug>/index.html`**:

1. Top bar — back link, project index (`07 / 32`), prev/next
2. Project hero — sectors eyebrow, h1 title, client, year, description
3. Gallery — stacked full-width images in `projects.json` order
4. Footer — contact

Project pages render completely without JavaScript. JS adds only the lightbox
on project pages and the sector filter on the index.

## 7. Design system

### 7.1 Typography

Onest, weights 400 / 500 / 600, self-hosted WOFF2, preloaded, `font-display: swap`.

| Role | Size | Line height | Letter spacing | Weight |
|:--|:--|:--|:--|:--|
| Display | `clamp(3.2rem, 11vw, 9.5rem)` | 0.92 | −0.04em | 500 |
| H2 | `clamp(2.2rem, 6vw, 5rem)` | 1.0 | −0.03em | 500 |
| H3 | `clamp(1.4rem, 2.4vw, 2rem)` | 1.15 | −0.02em | 500 |
| Lead | `clamp(1.15rem, 1.8vw, 1.6rem)` | 1.35 | −0.01em | 400 |
| Body | 1.0625rem | 1.6 | 0 | 400 |
| Micro label | 0.75rem, uppercase | 1.2 | 0.08em | 500 |

### 7.2 Colour

| Token | Value | Contrast on white | Permitted use |
|:--|:--|:--|:--|
| `--bg` | `#ffffff` | — | page ground |
| `--ink` | `#000000` | 21:1 | headings, primary text |
| `--body` | `#606060` | 5.92:1 | body copy, all text < 24 px |
| `--muted` | `#8d8d8d` | 3.03:1 | **text ≥ 24 px only** |
| `--surface` | `#f2f2f2` | — | alternate section ground |
| `--rule` | `rgba(0,0,0,0.16)` | — | decorative hairlines only |
| `--focus` | `#000000` | 21:1 | 2 px focus ring |

The reference site uses `#8d8d8d` for body copy. At 3.03:1 that fails WCAG
2.2 SC 1.4.3, so it is restricted here to text at or above 24 px, where the
3:1 large-text threshold applies. Colour never carries meaning on its own
(W07); active filter state is conveyed by fill inversion plus
`aria-pressed`.

### 7.3 Layout

- 12-column grid, gutter `clamp(16px, 2vw, 32px)`.
- Page padding `clamp(20px, 4vw, 64px)`; max content width 1720 px.
- Square corners on images and cards; pill buttons.
- Shared hard left alignment edge across all headings and lists (W10). Body
  text is never centred.
- Work grid: 1 column below 640 px, 2 up to 1024 px, 3 above.

### 7.4 Motion

Reveal on scroll: opacity 0→1 plus 16 px rise, 0.7 s
`cubic-bezier(0.16, 1, 0.3, 1)`, via `IntersectionObserver`. Fully disabled
under `prefers-reduced-motion: reduce`. No scroll hijacking, no parallax.

## 8. Compliance mapping

Against `llm-guideline-01-websites.md` §10:

| Check | How it is met |
|:--|:--|
| W01 purpose + CTA in first 1080 px | Hero h1, lead and "View work" button sit above 1080 px at 1440×900 |
| W08 content cut at fold | Work-grid first row intentionally crosses the fold on the index; gallery first image crosses it on project pages |
| W02 text ≥ 4.5:1 | `--body #606060` at 5.92:1; `--muted` gated to ≥ 24 px |
| W03 non-text ≥ 3:1 | Focus ring and button fills are pure black |
| W04/W40/W41 target size | Filter pills, pager buttons and lightbox controls ≥ 44×44 px |
| W05 explicit dimensions | Every `img` gets `width`/`height` from `images.json` |
| W06 focus indicator | Global `:focus-visible` 2 px black outline, 2 px offset |
| W07 no colour-only meaning | Active filter uses fill inversion + `aria-pressed` |
| W09 landmarks, one h1 | `header`/`nav`/`main`/`footer`; exactly one h1 per page |
| W10 shared left edge | Single grid origin for all headings and lists |
| W13 labelled groups | Every section carries a visible heading |
| W20 broad navigation | Flat nav: Work, Studio, Capabilities, Contact |
| W24 one primary CTA | "View work" primary; contact link secondary |
| W30 LCP preloaded | Hero preloaded; first three grid thumbs eager + `fetchpriority="high"`; rest lazy |
| W32 font loading | Onest self-hosted, preloaded, `font-display: swap` |
| W53 form labels | No forms on the site — not applicable |

No claim from §9 of the guideline is reproduced.

## 9. Content parity

The following must be identical to the existing site:

- 32 projects, in `projects.json` array order (alphabetical by slug).
- Every project `description`, verbatim.
- Every project `gallery` array, in the same sequence.
- The same `thumbnail` per project.
- Hero, studio/process, capabilities, sectors and contact copy, verbatim from
  `portfolio-repo/index.html`.
- Contact details: `hethusha@gmail.com`, `+971 55 244 2540`,
  `+971 50 512 6217`, Dubai, UAE.

Only the derivative image *format and resolution* change. Cropping, ordering
and selection do not.

### 9.1 Known data gap

`JETEX-AERO-2026` has an empty `description` and an empty `client` in the
source data. Per the content-parity decision, this is carried over as-is: the
project page renders title, sectors and gallery, and omits the description and
client blocks entirely rather than emitting empty elements. This is a
pre-existing gap in the source data, not a regression.

## 10. Verification

Before the work is called complete:

1. `build_images.py` reports 356/356 sources processed, 0 errors.
2. `build_site.py` emits `index.html` + exactly 32 project pages.
3. A parity script asserts, against `projects.json`: 32 pages exist; each
   page's gallery `img` count equals `len(gallery)`; each non-empty
   description appears verbatim in its page.
4. Every `<img>` in the output carries `width` and `height`.
5. Served locally and loaded; index and a sample project page render.
6. Repo pushed; Pages build succeeds; live URL returns 200 and the old site at
   `/portfolio/` still returns 200 and is unchanged.
