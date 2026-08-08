# Social posts — how this works

Four posts are built and waiting. **Nothing will publish until you approve it.**

Built against `OBNOTES/llm-guideline-12-social-posts-ochre-voice.md` (voice,
canvas, gates) and `llm-guideline-13-social-asset-generation.md` (SVG → PNG
pipeline, automation).

---

## What you need to do

### Once, at the start

1. **Create the accounts.** LinkedIn (you may already have one) and an
   Instagram **professional** account. Use your real name. Keep them in a
   separate browser profile, and turn every notification off.
2. **Connect IFTTT.** Free account, then create one applet:
   - **If This** → RSS Feed → *New feed item*
   - Feed URL: `https://unrealumanga.github.io/portfolio3/social/feed.xml`
   - **Then That** → LinkedIn → *Share an update with image*
   - Message: `{{EntryContent}}` — Image URL: `{{EntryImageUrl}}`

   That is your one applet spent. Keep the second in reserve.
3. **Instagram is manual.** IFTTT cannot publish to Instagram — Meta does not
   expose it. Use Meta Business Suite to batch-schedule, roughly 20 minutes a
   month.

### Before each post goes out

1. Open `social/queue.json`.
2. Fill any `[ ... ]` blanks in the `caption`. These are facts only you know —
   the fabrication partner, what The 4th Room actually did. **Never leave a
   bracket in.** The publisher refuses to run if one is still there.
3. Change `"approved": false` to `"approved": true`.
4. Commit and push. That is the whole approval step.

Every Tuesday at 10:00 Dubai the workflow takes the next approved post and puts
it in the feed. IFTTT sees it and posts it. If nothing is approved, nothing
happens — it is safe to leave the queue empty for weeks.

To publish immediately instead of waiting: GitHub → **Actions** →
*social-queue* → **Run workflow**.

---

## The four posts

| # | Post | Type | Card | Blanks to fill |
|:--|:--|:--|:--|:--|
| 01 | Carrying the Mountain to the Guest | project | photo | fabrication partner |
| 02 | Turning Numbers Into Rooms | project | photo | partner + what The 4th Room did |
| 03 | Turning Cybersecurity Into Spectacle | project | photo | fabrication partner |
| 04 | Directing Scenes Instead of Software | pipeline | statement | none |

Post 04 needs nothing from you and can go out first if you'd rather start
without homework.

---

## Regenerating the artwork

```sh
python3 social/generate.py      # SVG → measured fit → PNG
python3 social/verify_post.py   # GATES 1-6, all measured
```

`generate.py` requires Onest installed as a **system** font — the site's woff2
is not enough for Inkscape:

```sh
curl -sL -o ~/.local/share/fonts/Onest.ttf \
  "https://github.com/google/fonts/raw/main/ofl/onest/Onest%5Bwght%5D.ttf"
fc-cache -f
```

---

## Design decisions worth knowing

**The palette is yours, not the guideline's.** `tokens.json` is extracted from
the live portfolio2 stylesheet — `#f3f4ef` paper, `#11120f` ink, `#d9ff43`
acid. The guideline's §5.1 values are explicitly flagged there as placeholders,
so they are not used. No Ochre mark, colour or wordmark appears anywhere
(GATE 6): Ochre supplies sentence cadence only.

**Acid only works on dark.** Measured: `#d9ff43` on paper is **1.04:1** —
effectively invisible. On the dark ground it is **16.44:1**. That single
measurement is why statement cards use a dark ground; it is the only ground
where the accent can carry meaning. `verify_post.py` fails the build if paper
and acid ever appear in the same frame.

**Photos are never cropped.** The guideline's archetype A specifies a full-bleed
photograph, but every source image is 16:9. Covering a 4:5 frame from 16:9
discards about 55% of the image width, which wrecks a deliberately composed
render. So the photo sits at its native 16:9 across the full width and the
title goes beneath it. Nothing is cropped.

**The photo band starts at y=135, not y=0.** LinkedIn crops 4:5 to the central
square on desktop. A band at y=0 would lose its top 135px there. Starting at
the crop line means the photograph survives both crops whole.

**Two corrections to the guidelines**, found while building:

- `--export-png-antialias` is listed as grade `[A]` in LLM-SOC-013 §0, but
  Inkscape 1.2.2 rejects it outright: `Unknown option`. It is version-dependent
  and is not used here. Antialiasing is on by default.
- LLM-SOC-013 §6's `pop_queue.py` emits `title + "\n\n" + caption`. Our captions
  already open with the title, as GATE 1 requires, so that would print it twice.
  The caption is used verbatim.

**Caption length.** §3.1 targets 900–1600 characters. Posts 02 and 03 come in
under that. Padding them would breach the coherence principle, which the same
guideline grades `[A]` and calls its strongest transfer, so short captions are
a warning here rather than a failure. Filling the blanks lifts both into range.
