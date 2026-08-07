#!/usr/bin/env python3
"""Generate WebP derivatives for every image the live portfolio references.

Sources live in /home/mnm/AI_Lab/Workspace/portfolio/img and are already
web-sized (1100x614 and 1600x900, ~19.5 MB total). They are read only, never
modified. Two derivatives are written per source:

    <name>-640.webp     narrow cards, mobile
    <name>-1600.webp    wide cards, gallery, lightbox

Neither upscales; a source narrower than the target keeps its own width.
Intrinsic dimensions land in data/images.json so every <img> can carry explicit
width and height.
"""

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = Path("/home/mnm/AI_Lab/Workspace/portfolio")
OUT_ROOT = ROOT / "assets" / "img"

WIDTHS = {640: 82, 1600: 80}
EXTRA = ["img/hero.jpg"]


def derivative_name(rel_path, width):
    stem = Path(rel_path).stem
    safe = "".join(c if (c.isalnum() or c in "-_") else "-" for c in stem)
    safe = "-".join(filter(None, safe.split("-")))[:70].strip("-_") or "image"
    digest = hashlib.blake2b(rel_path.encode("utf-8"), digest_size=3).hexdigest()
    return f"assets/img/{safe}-{digest}-{width}.webp"


def collect_sources():
    """Every distinct image referenced by site.json, order preserved."""
    site = json.loads((ROOT / "data" / "site.json").read_text())
    seen, ordered = set(), []

    def add(ref):
        if ref and ref not in seen:
            seen.add(ref)
            ordered.append(ref)

    for ref in EXTRA:
        add(ref)
    for card in site["featured"]:
        add(card["kv"])
    for gallery in site["galleries"].values():
        for image in gallery["images"]:
            add(image["src"])
    return ordered


def build_one(rel_path, force=False):
    source = SOURCE_ROOT / rel_path
    if not source.exists():
        return None, f"missing source: {rel_path}"

    entry, pending = {}, []
    for width in WIDTHS:
        out_rel = derivative_name(rel_path, width)
        out_abs = ROOT / out_rel
        if (
            not force
            and out_abs.exists()
            and out_abs.stat().st_mtime >= source.stat().st_mtime
        ):
            with Image.open(out_abs) as done:
                entry[str(width)] = {"src": out_rel, "w": done.width, "h": done.height}
        else:
            pending.append((width, out_rel, out_abs))

    if not pending:
        return entry, None

    try:
        with Image.open(source) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            for width, out_rel, out_abs in pending:
                out_abs.parent.mkdir(parents=True, exist_ok=True)
                target = min(width, img.width)
                height = max(1, round(img.height * target / img.width))
                resized = img.resize((target, height), Image.LANCZOS)
                resized.save(out_abs, "WEBP", quality=WIDTHS[width], method=6)
                entry[str(width)] = {"src": out_rel, "w": target, "h": height}
    except Exception as exc:  # noqa: BLE001 - report and continue over the set
        return None, f"{rel_path}: {exc}"

    return entry, None


def main():
    force = "--force" in sys.argv
    sources = collect_sources()
    print(f"{len(sources)} referenced images")

    index, errors = {}, []
    for i, rel_path in enumerate(sources, 1):
        entry, err = build_one(rel_path, force=force)
        if err:
            errors.append(err)
        else:
            index[rel_path] = entry
        if i % 40 == 0 or i == len(sources):
            print(f"  {i}/{len(sources)}", flush=True)

    (ROOT / "data" / "images.json").write_text(
        json.dumps(index, indent=1, sort_keys=True) + "\n"
    )

    files = list(OUT_ROOT.rglob("*.webp"))
    total = sum(f.stat().st_size for f in files)
    print(f"\nprocessed : {len(index)}/{len(sources)}")
    print(f"errors    : {len(errors)}")
    for err in errors:
        print(f"  ! {err}")
    print(f"output    : {total / 1048576:.1f} MB across {len(files)} files")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
