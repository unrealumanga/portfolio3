#!/usr/bin/env python3
"""Add a project to data/site.json from a folder with a nested `selected/` dir.

    scripts/add_project.py KEY "Title" "Client" "Type" YEAR "/path/to/folder" [--front]

Images in <folder>/selected are naturally sorted (so 0000_ / 0001_ / 1. / 3. /
10. order correctly); the first one is the cover and the card key visual.
Each is resized to max 2000 px wide JPEG into sources/<KEY>/NN.jpg (the build
reads `sources/...` refs from this repo; everything else from the live
portfolio's img/ dir). Then run build_images.py, build_site.py, verify.py.

--front puts the featured card at the top of the grid (wide/narrow alternate:
new cards are inserted in pairs so the rhythm is kept by the caller).
"""

import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def natural(name):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    key, title, client, kind, year, folder = args[:6]
    span = next((a.split("=")[1] for a in sys.argv if a.startswith("--span=")), "wide")
    at = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--at=")), None)

    sel = Path(folder) / "selected"
    files = sorted(
        (f for f in sel.iterdir() if f.suffix.lower() in EXTS), key=lambda f: natural(f.name)
    )
    out_dir = ROOT / "sources" / key
    out_dir.mkdir(parents=True, exist_ok=True)

    images = []
    for i, f in enumerate(files):
        with Image.open(f) as im:
            im = ImageOps.exif_transpose(im).convert("RGB")
            if im.width > 2000:
                im = im.resize((2000, round(im.height * 2000 / im.width)), Image.LANCZOS)
            dest = out_dir / f"{i:02d}.jpg"
            im.save(dest, "JPEG", quality=88, optimize=True)
        images.append({"src": f"sources/{key}/{i:02d}.jpg", "cap": title})

    path = ROOT / "data" / "site.json"
    site = json.loads(path.read_text())
    if key in site["galleries"]:
        raise SystemExit(f"{key} already exists")

    site["galleries"][key] = {"name": title, "images": images}
    card = {"key": key, "span": span, "title": title, "client": client,
            "type": kind, "year": year, "kv": images[0]["src"]}
    if at is None:
        site["featured"].append(card)
    else:
        site["featured"].insert(at, card)

    # index: alphabetical by client (stable), then renumber 01..N
    row = {"no": "", "title": title, "client": client, "type": kind, "year": year, "key": key}
    idx = site["index"]
    pos = next((i for i, r in enumerate(idx) if r["client"].lower() > client.lower()), len(idx))
    idx.insert(pos, row)
    for n, r in enumerate(idx, 1):
        r["no"] = f"{n:02d}"

    # sector counts follow the index
    plural = {"Exhibition": "Exhibitions", "Brand Space": "Brand Spaces",
              "Pavilion": "Pavilions", "Corporate": "Corporate", "Conference": "Conference"}
    for s in site["sectors"]:
        n = sum(1 for r in idx if plural.get(r["type"]) == s["name"])
        s["count"] = f"{n:02d} project" + ("" if n == 1 else "s")

    path.write_text(json.dumps(site, indent=1, ensure_ascii=False) + "\n")
    print(f"{key}: {len(images)} images, cover {files[0].name}")


if __name__ == "__main__":
    main()
