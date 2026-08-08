#!/usr/bin/env python3
"""Generate 1080x1350 social flyers as SVG, fit the title by measurement, export PNG.

Implements LLM-SOC-013 stages S2 (generator) and S3 (measure / shrink / export),
using the user's own portfolio2 tokens rather than the guideline's placeholders.

One deliberate deviation from LLM-SOC-012 §5.2 archetype A, recorded here:

    The guideline specifies a full-bleed photograph. Every source image in the
    archive is 16:9 (1600x900 or 1100x614). Covering a 4:5 frame from a 16:9
    source discards ~55% of the image width, which destroys the composition of
    a deliberately framed architectural render. So archetype A places the
    photograph at its NATIVE 16:9 across the full width (1080x608) and sets the
    title on a block beneath it. Nothing is cropped. The coherence, signalling
    and contiguity rules the guideline actually cares about are unaffected, and
    GATE 2's central-square requirement is still met.
"""

import json
import re
import subprocess
import sys
import xml.sax.saxutils as sx
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TOKENS = json.loads((HERE / "tokens.json").read_text())
C = TOKENS["colors"]
FONT_FAMILY = TOKENS["type"]["fallback"]
FONT_PATH = Path.home() / ".local/share/fonts/Onest.ttf"

W, H = 1080, 1350
MARGIN = 80
SAFE_W = W - 2 * MARGIN                 # 920
CORE_TOP = (H - W) // 2                 # 135
CORE_BOTTOM = CORE_TOP + W              # 1215 — desktop crop floor
IMG_H = round(W * 900 / 1600)           # 608 — native 16:9 band
# Start the photo at the desktop-crop line rather than at y=0. LinkedIn crops
# 4:5 to the central square on desktop, so a band at y=0 would lose its top
# 135 px (22% of the image) there. Starting at CORE_TOP means the photograph is
# whole in both crops, and the paper strip above it reads as a top margin.
IMG_Y = CORE_TOP                        # 135


# ---------------------------------------------------------------- metrics
def metric_fn(px, weight=500):
    """width(text) -> px. Uses the real Onest face so the first guess is close."""
    try:
        from PIL import ImageFont

        f = ImageFont.truetype(str(FONT_PATH), px)
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
        return lambda s: f.getbbox(s)[2] - f.getbbox(s)[0]
    except Exception:
        # Grotesque average advance; the Inkscape fit loop corrects any error.
        return lambda s: len(s) * px * 0.52


def wrap(text, max_px, measure):
    words, lines, cur = text.split(), [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if measure(trial) <= max_px or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def tspans(lines, x, leading):
    return "".join(
        f'<tspan x="{x}" dy="{0 if i == 0 else leading}">{sx.escape(ln)}</tspan>'
        for i, ln in enumerate(lines)
    )


# ---------------------------------------------------------------- archetypes
def archetype_A(cfg, measure):
    """IMAGE-LED. Native 16:9 photo band, paper block beneath, ink title."""
    size = cfg["title_px"]
    leading = round(size * 1.06)
    lines = wrap(cfg["title"], SAFE_W, measure)
    title_y = IMG_Y + IMG_H + 90 + size * 0.78
    meta_y = CORE_BOTTOM - 46          # stays above the desktop crop
    return f"""<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" fill="{C['paper']}"/>
  <image xlink:href="{sx.escape(cfg['image'])}" x="0" y="{IMG_Y}"
         width="{W}" height="{IMG_H}" preserveAspectRatio="xMidYMid slice"/>
  <text id="title" x="{MARGIN}" y="{title_y:.0f}" fill="{C['ink']}"
        font-family="{FONT_FAMILY}" font-size="{size}" font-weight="500"
        letter-spacing="{-size * 0.03:.1f}">{tspans(lines, MARGIN, leading)}</text>
  <line x1="{MARGIN}" y1="{meta_y - 44}" x2="{MARGIN + 96}" y2="{meta_y - 44}"
        stroke="{C['ink']}" stroke-width="3"/>
  <text id="meta" x="{MARGIN}" y="{meta_y}" fill="{C['ink_soft']}"
        font-family="{FONT_FAMILY}" font-size="27" font-weight="500"
        letter-spacing="1.6">{sx.escape(cfg.get('meta', ''))}</text>
</svg>"""


def archetype_B(cfg, measure):
    """STATEMENT. Dark ground — the only ground where acid clears 4.5:1."""
    size = cfg["title_px"]
    leading = round(size * 1.08)
    lines = wrap(cfg["title"], SAFE_W, measure)
    block_h = leading * (len(lines) - 1)
    title_y = (H - block_h) / 2 - 40 + size * 0.36
    rule_y = title_y + block_h + 76
    return f"""<svg xmlns="http://www.w3.org/2000/svg"
     width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" fill="{C['dark']}"/>
  <text id="title" x="{MARGIN}" y="{title_y:.0f}" fill="{C['white']}"
        font-family="{FONT_FAMILY}" font-size="{size}" font-weight="500"
        letter-spacing="{-size * 0.03:.1f}">{tspans(lines, MARGIN, leading)}</text>
  <line x1="{MARGIN}" y1="{rule_y:.0f}" x2="{MARGIN + 120}" y2="{rule_y:.0f}"
        stroke="{C['acid']}" stroke-width="4"/>
  <text id="meta" x="{MARGIN}" y="{CORE_BOTTOM - 46}" fill="{C['acid']}"
        font-family="{FONT_FAMILY}" font-size="27" font-weight="500"
        letter-spacing="1.6">{sx.escape(cfg.get('meta', ''))}</text>
</svg>"""


ARCHETYPES = {"A": archetype_A, "B": archetype_B}


def build(cfg, out_svg):
    measure = metric_fn(cfg["title_px"])
    out_svg.write_text(ARCHETYPES[cfg["archetype"]](cfg, measure), encoding="utf-8")
    return out_svg


# ---------------------------------------------------------------- S3 fit loop
def query_bbox(svg, obj_id):
    vals = {}
    for flag, key in (
        ("--query-x", "x"),
        ("--query-y", "y"),
        ("--query-width", "w"),
        ("--query-height", "h"),
    ):
        try:
            out = subprocess.run(
                ["inkscape", f"--query-id={obj_id}", flag, str(svg)],
                capture_output=True, text=True, timeout=90,
            )
            m = re.search(r"-?\d+\.?\d*", out.stdout)
            if not m:
                return None
            vals[key] = float(m.group())
        except Exception:
            return None
    return vals["x"], vals["y"], vals["w"], vals["h"]


def fit_title(cfg, out_svg, max_h, floor_px=44, step=4):
    """Shrink until the measured title fits. Never trust the estimate."""
    px = cfg["title_px"]
    while px >= floor_px:
        cfg["title_px"] = px
        build(cfg, out_svg)
        bbox = query_bbox(out_svg, "title")
        if bbox is None:
            print(f"    WARN: query failed, accepting {px}px unverified")
            return px, None
        _, y, w, h = bbox
        if w <= SAFE_W and h <= max_h:
            print(f"    fit {px}px — measured {w:.0f}x{h:.0f}, bottom y={y + h:.0f}")
            return px, bbox
        px -= step
    print(f"    WARN: hit floor {floor_px}px — shorten the title")
    return floor_px, query_bbox(out_svg, "title")


def export_png(svg, png):
    """Export at exact pixel dimensions.

    LLM-SOC-013 lists --export-png-antialias as grade [A], but Inkscape 1.2.2
    rejects it outright ("Unknown option"). It is version-dependent, so it is
    not used here; antialiasing is on by default anyway. Width and height are
    passed explicitly to avoid the DPI-rounding failure in that guide's §7.
    """
    result = subprocess.run(
        ["inkscape", str(svg), "--export-type=png",
         f"--export-filename={png}", "--export-overwrite",
         "--export-area-page", f"--export-width={W}", f"--export-height={H}"],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"inkscape export failed: {result.stderr.strip()[:300]}")
    return png


def main():
    if not FONT_PATH.exists():
        print(f"FAIL: {FONT_PATH} missing — Inkscape would silently substitute.")
        return 1
    check = subprocess.run(["fc-list"], capture_output=True, text=True)
    if "Onest" not in check.stdout:
        print("FAIL: Onest not registered with fontconfig. Run fc-cache -f.")
        return 1

    queue = json.loads((HERE / "queue.json").read_text())
    src_dir, png_dir = HERE / "src", HERE / "png"
    src_dir.mkdir(exist_ok=True)
    png_dir.mkdir(exist_ok=True)

    for item in queue:
        art = item["archetype"]
        cfg = {
            "archetype": art,
            "title": item["title"],
            "meta": item["meta"],
            "title_px": 96 if art == "B" else 82,
        }
        if art == "A":
            image = Path(item["image_source"])
            if not image.exists():
                print(f"  ! {item['id']}: source image missing: {image}")
                continue
            cfg["image"] = str(image)
            # Title must clear the metadata rule inside the desktop-crop band.
            max_h = (CORE_BOTTOM - 130) - (IMG_Y + IMG_H + 90)
        else:
            max_h = 620

        svg = src_dir / f"{item['id']}.svg"
        print(f"  {item['id']} [{art}]")
        fit_title(cfg, svg, max_h=max_h)
        export_png(svg, png_dir / f"{item['id']}.png")

    print(f"\n{len(queue)} assets in {png_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
