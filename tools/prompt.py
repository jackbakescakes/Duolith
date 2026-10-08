#!/usr/bin/env python3
"""Print a precise Gemini image prompt for a sprite defined in tools/sprites.json.

    python3 tools/prompt.py zombie
    python3 tools/prompt.py zombie --transparent    # ask for a real alpha background instead of magenta
    python3 tools/prompt.py --list

Default asks for a flat magenta (#FF00FF) background, because image models usually hand back an opaque
image even when asked for "transparent" (often with a painted checkerboard). downscale.py removes the
magenta for you, giving a true transparent PNG. Use --transparent only if your Gemini output really
does come back with alpha (check by opening it over a coloured background).
"""
import argparse, json, sys
from pathlib import Path

SPEC = Path(__file__).with_name("sprites.json")


def build(name, spec, data, transparent):
    w, h = spec["size"]
    tile = spec.get("tile", False)
    cols = data.get("max_colours", 16)
    lines = [f"Pixel art game asset: {spec['desc']}.", ""]
    lines.append(f"Style: {data['style']}. Limited palette of at most {cols} colours.")
    lines.append(
        f"Target resolution: this will be shrunk to exactly {w}x{h} pixels in-game, so draw it as a "
        f"chunky {w}x{h} pixel grid (each 'pixel' a crisp square block), not as a detailed illustration. "
        "Strong readable silhouette, no fine detail that would disappear at that size."
    )
    if tile:
        lines.append(
            "It must tile seamlessly: left edge matches right edge and top edge matches bottom edge. "
            "Fill the whole canvas edge to edge, no border, no vignette, no transparency."
        )
    else:
        lines.append(
            "Centre the subject and fill most of the canvas, with only a thin even margin. "
            "Single subject only, no duplicates, no sprite sheet, no variations."
        )
        if transparent:
            lines.append("Background: fully transparent (real alpha channel), no ground, no cast shadow, no checkerboard.")
        else:
            lines.append(
                "Background: one flat solid pure magenta (#FF00FF) filling everything outside the subject, "
                "with no ground, no cast shadow, no gradient, no checkerboard. Do not use magenta anywhere on the subject."
            )
    lines.append("Square 1:1 image. No text, no watermark, no frame.")
    lines.append("")
    key = "" if (tile or not spec.get("key", True) or transparent) else " --key '#FF00FF'"
    lines.append("After generating:")
    lines.append(f"  1. save the file as art-src/{name}.png")
    lines.append(f"  2. python3 tools/downscale.py art-src/{name}.png --sprite {name}")
    if transparent and not tile:
        lines.append("     (if the background is not already transparent, add --key '#FF00FF' or your background colour)")
    elif key:
        lines.append("     (reads size, output path and magenta key from sprites.json)")
    lines.append("  3. python3 tools/check_assets.py")
    return "\n".join(lines)


def main():
    data = json.loads(SPEC.read_text())
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sprite", nargs="?")
    ap.add_argument("--transparent", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list or not a.sprite:
        for n, s in data["sprites"].items():
            print(f"{n:8s} {s['size'][0]}x{s['size'][1]:<3d} {s['file']}")
        return
    if a.sprite not in data["sprites"]:
        sys.exit(f"unknown sprite '{a.sprite}'. Known: {', '.join(data['sprites'])}")
    print(build(a.sprite, data["sprites"][a.sprite], data, a.transparent))


if __name__ == "__main__":
    main()
