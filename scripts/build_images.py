#!/usr/bin/env python3
"""Generate WebP derivatives for every image referenced by data/projects.json.

Sources are read from the existing portfolio repo and never modified. Two
derivatives are written per source image:

    <name>-640.webp    work-grid cards
    <name>-1920.webp   project gallery and lightbox

Intrinsic dimensions for both are recorded in data/images.json so every <img>
in the generated HTML can carry explicit width and height (CLS).
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = Path("/home/mnm/AI_Lab/Workspace/portfolio-repo")
OUT_ROOT = ROOT / "assets" / "img"

# 640 for 1x cards and mobile, 1280 for 2x cards, 1920 for gallery and lightbox.
WIDTHS = {640: 80, 1280: 78, 1920: 78}


def derivative_name(rel_path, width):
    """assets/img/<slug>/<stem>-<hash>-<width>.webp for a projects/<slug>/<file>.

    Source filenames differ in ways that slugify identically -- Beeah alone has
    both "18. Majilis Area_upscale01.jpg" and "18.-Majilis-Area_upscale01.jpg".
    A hash of the full source path keeps distinct sources on distinct outputs.
    """
    parts = Path(rel_path).parts
    slug = parts[1] if len(parts) > 2 else "misc"
    stem = Path(rel_path).stem
    safe = "".join(c if (c.isalnum() or c in "-_") else "-" for c in stem)
    safe = "-".join(filter(None, safe.split("-")))[:70].strip("-_") or "image"
    digest = hashlib.blake2b(rel_path.encode("utf-8"), digest_size=4).hexdigest()
    return f"assets/img/{slug}/{safe}-{digest}-{width}.webp"


def collect_sources():
    """Every distinct image path referenced by projects.json, order preserved."""
    projects = json.loads((ROOT / "data" / "projects.json").read_text())
    seen, ordered = set(), []
    for project in projects:
        refs = [project.get("thumbnail")] + list(project.get("gallery") or [])
        for ref in refs:
            if ref and ref not in seen:
                seen.add(ref)
                ordered.append(ref)
    return ordered


VIDEO_EXTS = {".mp4", ".webm", ".mov"}


def build_video(rel_path, force=False):
    """Transcode a gallery video and extract a poster frame.

    One gallery item is a 45 MB, 51 s, 720p h264 clip at roughly 7 Mbps. It is
    re-encoded at the same resolution with a sane bitrate and faststart, which
    is the same format-and-resolution-only change applied to the stills.
    """
    source = SOURCE_ROOT / rel_path
    if not source.exists():
        return None, f"missing source: {rel_path}"

    parts = Path(rel_path).parts
    slug = parts[1] if len(parts) > 2 else "misc"
    digest = hashlib.blake2b(rel_path.encode("utf-8"), digest_size=4).hexdigest()
    stem = Path(rel_path).stem
    safe = "".join(c if (c.isalnum() or c in "-_") else "-" for c in stem)
    safe = "-".join(filter(None, safe.split("-")))[:70].strip("-_") or "video"

    vid_rel = f"assets/img/{slug}/{safe}-{digest}.mp4"
    poster_rel = f"assets/img/{slug}/{safe}-{digest}-poster.webp"
    vid_abs, poster_abs = ROOT / vid_rel, ROOT / poster_rel
    vid_abs.parent.mkdir(parents=True, exist_ok=True)

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x",
         str(source)],
        capture_output=True, text=True, check=False,
    )
    try:
        width, height = (int(v) for v in probe.stdout.strip().split("x")[:2])
    except ValueError:
        return None, f"{rel_path}: could not probe dimensions"

    stale = force or not vid_abs.exists() or \
        vid_abs.stat().st_mtime < source.stat().st_mtime
    if stale:
        enc = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
             "-c:v", "libx264", "-crf", "24", "-preset", "slow",
             "-pix_fmt", "yuv420p", "-movflags", "+faststart",
             "-c:a", "aac", "-b:a", "128k", str(vid_abs)],
            capture_output=True, text=True, check=False,
        )
        if enc.returncode != 0:
            return None, f"{rel_path}: ffmpeg {enc.stderr.strip()[:160]}"

    if force or not poster_abs.exists():
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-i", str(source),
             "-frames:v", "1", "-q:v", "80", str(poster_abs)],
            capture_output=True, text=True, check=False,
        )
    if not poster_abs.exists():
        return None, f"{rel_path}: poster extraction failed"

    with Image.open(poster_abs) as poster:
        pw, ph = poster.size

    entry = {
        "type": "video",
        "video": vid_rel,
        "poster": {"src": poster_rel, "w": pw, "h": ph},
        "w": width,
        "h": height,
    }
    return entry, None


def build_one(rel_path, force=False):
    """Return {width: {src, w, h}} for one source image, generating as needed."""
    source = SOURCE_ROOT / rel_path
    if not source.exists():
        return None, f"missing source: {rel_path}"

    entry = {}
    pending = []
    for width in WIDTHS:
        out_rel = derivative_name(rel_path, width)
        out_abs = ROOT / out_rel
        fresh = (
            not force
            and out_abs.exists()
            and out_abs.stat().st_mtime >= source.stat().st_mtime
        )
        if fresh:
            with Image.open(out_abs) as done:
                entry[str(width)] = {"src": out_rel, "w": done.width, "h": done.height}
        else:
            pending.append((width, out_rel, out_abs))

    if not pending:
        return entry, None

    try:
        with Image.open(source) as img:
            # Honour EXIF orientation, then drop the tag so it is not applied twice.
            img = ImageOps.exif_transpose(img)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            for width, out_rel, out_abs in pending:
                out_abs.parent.mkdir(parents=True, exist_ok=True)
                # Never upscale: a narrower source keeps its own width.
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
        if Path(rel_path).suffix.lower() in VIDEO_EXTS:
            entry, err = build_video(rel_path, force=force)
        else:
            entry, err = build_one(rel_path, force=force)
        if err:
            errors.append(err)
        else:
            index[rel_path] = entry
        if i % 25 == 0 or i == len(sources):
            print(f"  {i}/{len(sources)}", flush=True)

    (ROOT / "data" / "images.json").write_text(
        json.dumps(index, indent=1, sort_keys=True) + "\n"
    )

    total = sum(
        f.stat().st_size for f in OUT_ROOT.rglob("*.webp") if f.is_file()
    )
    print(f"\nprocessed : {len(index)}/{len(sources)}")
    print(f"errors    : {len(errors)}")
    for err in errors:
        print(f"  ! {err}")
    print(f"output    : {total / 1048576:.1f} MB across "
          f"{sum(1 for _ in OUT_ROOT.rglob('*.webp'))} files")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
