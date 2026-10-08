#!/usr/bin/env python3
"""Report which sprites exist, whether sizes match the spec, and whether index.html agrees with sprites.json.

    python3 tools/check_assets.py

Exit code 1 if an existing asset has the wrong size, or index.html and sprites.json disagree.
Missing assets are fine (the game draws placeholders for them).
"""
import json, re, sys
from pathlib import Path

from PIL import Image


def pixels(img):
    """Pixel iterator that works on old and new Pillow."""
    return img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata()

ROOT = Path(__file__).resolve().parent.parent
spec = json.loads((ROOT / "tools" / "sprites.json").read_text())["sprites"]
html = (ROOT / "index.html").read_text()

block = re.search(r"const ASSET_FILES = \{(.*?)\};", html, re.S)
in_html = dict(re.findall(r"(\w+):\s*'([^']+)'", block.group(1))) if block else {}

bad = 0
total = 0
print(f"{'sprite':8s} {'status':9s} {'size':>8s} {'colours':>8s} {'bytes':>7s}")
for name, s in spec.items():
    path = ROOT / "assets" / s["file"]
    want = tuple(s["size"])
    if not path.exists():
        print(f"{name:8s} {'missing':9s} {'':>8s} {'':>8s} {'':>7s}  (placeholder in use; want {want[0]}x{want[1]})")
        continue
    img = Image.open(path).convert("RGBA")
    cols = len({p for p in pixels(img) if p[3]})
    b = path.stat().st_size
    total += b
    ok = img.size == want
    bad += not ok
    note = "" if ok else f"  WRONG SIZE, want {want[0]}x{want[1]}"
    print(f"{name:8s} {'ok' if ok else 'BAD':9s} {img.width:>3d}x{img.height:<4d} {cols:>8d} {b:>7d}{note}")

for name, s in spec.items():
    if in_html.get(name) != s["file"]:
        bad += 1
        print(f"MISMATCH: index.html ASSET_FILES[{name}] = {in_html.get(name)!r}, sprites.json says {s['file']!r}")
for name in in_html:
    if name not in spec:
        bad += 1
        print(f"MISMATCH: index.html loads '{name}' which is not in sprites.json")

stray = [p for p in (ROOT / "assets").rglob("*") if p.is_file() and p.name != ".gitkeep"
         and str(p.relative_to(ROOT / "assets")) not in {s["file"] for s in spec.values()}]
for p in stray:
    print(f"note: {p.relative_to(ROOT)} is not referenced by sprites.json")

print(f"total asset bytes: {total}")
sys.exit(1 if bad else 0)
