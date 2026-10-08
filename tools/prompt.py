#!/usr/bin/env python3
"""Print a Gemini image prompt for a sprite defined in tools/sprites.json.

    python3 tools/prompt.py zombie
    python3 tools/prompt.py zombie --transparent    # ask for a real alpha background instead of magenta
    python3 tools/prompt.py --list

Wording notes (learned the hard way with Gemini):
  * Ask for "an actual picture (an image file, not a text grid)". If the prompt leans on an exact pixel
    grid ("exactly 12x12 pixels"), Gemini tends to reply with an ASCII/colour-code grid instead of an image.
    The exact size is enforced afterwards by downscale.py, so the prompt only needs "chunky visible pixels".
  * Default asks for a flat magenta background, because image models usually return an opaque image even when
    asked for "transparent". downscale.py auto-detects the background colour and removes it. Use --transparent
    only if your Gemini output really does come back with alpha.
  * Gemini's download button saves a JPEG. That's fine: downscale.py reads JPEG or PNG.
"""
import argparse, json, sys
from pathlib import Path

SPEC = Path(__file__).with_name("sprites.json")


def build(name, spec, data, transparent):
    w, h = spec["size"]
    tile = spec.get("tile", False)
    cols = spec.get("colours", data.get("max_colours", 16))
    lines = [
        "Please create an actual picture (an image file, not a text grid): a 1:1 square image, "
        f"pixel art style with chunky visible square pixels, of {spec['desc']}.",
        "",
        f"Style: {data['style']}. Limited palette of at most {cols} colours.",
        f"It will be shrunk to roughly {w}x{h} pixels in the game, so keep the shapes bold and simple with a "
        "strong readable silhouette, and avoid fine detail that would disappear at that size.",
    ]
    if tile:
        lines.append(
            "It must tile seamlessly (left edge matches right edge, top edge matches bottom edge) and fill the "
            "whole frame edge to edge, with no border, no vignette, no objects and no text."
        )
    else:
        lines.append(
            "Centre the subject so it fills most of the frame with only a thin even margin. "
            "Single subject only: no duplicates, no sprite sheet, no variations."
        )
        if transparent:
            lines.append("The background must be fully transparent (real alpha), with no ground, no shadow, no checkerboard.")
        else:
            lines.append(
                "The whole background is one flat solid magenta (#FF00FF) with no ground, no shadow, no gradient "
                "and no checkerboard. Do not use magenta anywhere on the subject. No text."
            )
    lines.append("")
    lines.append("After generating:")
    lines.append(f"  1. download it and save it as art-src/{name}.jpg (or .png)")
    lines.append(f"  2. python3 tools/downscale.py art-src/{name}.jpg --sprite {name}")
    if not tile and transparent:
        lines.append("     (if the background is not already transparent, add --key auto)")
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
