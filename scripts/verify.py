#!/usr/bin/env python3
"""Assert content parity with the source data and the structural rules in the
design spec. Exits non-zero on any failure."""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

failures = []
checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        failures.append(message)


projects = json.loads((ROOT / "data" / "projects.json").read_text())
images = json.loads((ROOT / "data" / "images.json").read_text())

# --- Source parity: the copied data still matches the origin repo ---
origin = Path("/home/mnm/AI_Lab/Workspace/portfolio-repo/data/projects.json")
if origin.exists():
    check(
        origin.read_bytes() == (ROOT / "data" / "projects.json").read_bytes(),
        "projects.json differs from the source repo",
    )

check(len(projects) == 32, f"expected 32 projects, found {len(projects)}")

index_html = (ROOT / "index.html").read_text()

# --- Index ---
check("{{" not in index_html, "unsubstituted token in index.html")
check(index_html.count("<h1") == 1, "index.html must have exactly one h1 (W09)")
for landmark in ("<header", "<nav", "<main", "<footer"):
    check(landmark in index_html, f"index.html missing landmark {landmark} (W09)")
check(index_html.count('class="card"') == 32, "index.html must show all 32 cards")

# Card order must match projects.json order.
card_hrefs = re.findall(r'<a class="card" href="work/([^/]+)/"', index_html)
check(
    card_hrefs == [p["slug"] for p in projects],
    "work grid order does not match projects.json order",
)

# --- Project pages ---
for i, project in enumerate(projects):
    slug = project["slug"]
    page = ROOT / "work" / slug / "index.html"
    check(page.exists(), f"missing page for {slug}")
    if not page.exists():
        continue
    text = page.read_text()

    check("{{" not in text, f"{slug}: unsubstituted token")
    check(text.count("<h1") == 1, f"{slug}: must have exactly one h1 (W09)")

    # Gallery item count must equal the source gallery length.
    n_items = text.count('class="gallery-item"')
    check(
        n_items == len(project["gallery"]),
        f"{slug}: {n_items} gallery items, expected {len(project['gallery'])}",
    )

    # Gallery order must match the source array.
    rendered = re.findall(r'(?:data-full|<source src)="\.\./\.\./([^"]+)"', text)
    expected = []
    for ref in project["gallery"]:
        entry = images.get(ref, {})
        if entry.get("type") == "video":
            expected.append(entry["video"])
        else:
            tier = entry.get("1920") or entry.get("1280") or entry.get("640")
            if tier:
                expected.append(tier["src"])
    check(rendered == expected, f"{slug}: gallery order does not match source")

    # Description carried verbatim.
    description = (project.get("description") or "").strip()
    if description:
        check(
            html.escape(description, quote=True) in text,
            f"{slug}: description not present verbatim",
        )
    else:
        check(
            'class="lead project-description"' not in text,
            f"{slug}: empty description should render no description block",
        )

    # Client block only when the source has a client.
    if project.get("client"):
        check(f"<dd>{html.escape(project['client'])}</dd>" in text,
              f"{slug}: client missing")
    else:
        check("<dt>Client</dt>" not in text,
              f"{slug}: empty client should render no client block")

# --- W05: every img carries explicit width and height ---
for page in [ROOT / "index.html"] + sorted(ROOT.glob("work/*/index.html")):
    text = page.read_text()
    for tag in re.findall(r"<img\b[^>]*>", text):
        if 'id="lightbox-img"' in tag:
            continue  # sized at runtime, object-fit contained inside a fixed stage
        check(
            'width="' in tag and 'height="' in tag,
            f"{page.relative_to(ROOT)}: <img> without width/height (W05)",
        )
    for tag in re.findall(r"<video\b[^>]*>", text):
        check(
            'width="' in tag and 'height="' in tag,
            f"{page.relative_to(ROOT)}: <video> without width/height (W05)",
        )
    # Alt text on every content image.
    for tag in re.findall(r"<img\b[^>]*>", text):
        check('alt="' in tag, f"{page.relative_to(ROOT)}: <img> without alt")

# --- Referenced asset files actually exist ---
missing = set()
for page in [ROOT / "index.html"] + sorted(ROOT.glob("work/*/index.html")):
    text = page.read_text()
    base = page.parent
    for ref in re.findall(r'(?:src|href)="((?:\.\./)*assets/[^"]+)"', text):
        if not (base / ref).resolve().exists():
            missing.add(ref)
    for ref in re.findall(r'srcset="([^"]+)"', text):
        for part in ref.split(","):
            path = part.strip().split(" ")[0]
            if path and not (base / path).resolve().exists():
                missing.add(path)
check(not missing, f"{len(missing)} referenced assets missing: {sorted(missing)[:4]}")

# --- Internal links resolve ---
broken = set()
for page in [ROOT / "index.html"] + sorted(ROOT.glob("work/*/index.html")):
    base = page.parent
    for href in re.findall(r'href="((?:\.\./)*(?:work|index\.html)[^"#]*)"', page.read_text()):
        target = (base / href).resolve()
        if target.is_dir():
            target = target / "index.html"
        if not target.exists():
            broken.add(f"{page.relative_to(ROOT)} -> {href}")
check(not broken, f"broken internal links: {sorted(broken)[:4]}")

print(f"{checks - len(failures)}/{checks} checks passed")
for failure in failures:
    print(f"  FAIL {failure}")
raise SystemExit(1 if failures else 0)
