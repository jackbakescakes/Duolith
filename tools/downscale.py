#!/usr/bin/env python3
"""Turn a large Gemini image into a clean, tiny pixel-art PNG ready for assets/.

    python3 tools/downscale.py art-src/zombie.png --sprite zombie
    python3 tools/downscale.py art-src/thing.png assets/enemies/thing.png --size 16x16 --key '#FF00FF'

Steps: remove background colour (flood-filled from the edges, so interior pixels of the same colour
survive) -> crop to the subject -> shrink to fit the target size -> snap alpha to fully on/off ->
reduce to a small palette -> pad to exactly the target size -> save an optimised PNG.

--sprite NAME   take size, output path, anchor and key from tools/sprites.json
--size WxH      target pixel size (overrides the spec)
--key COLOUR    background colour to remove: '#RRGGBB' or 'auto' (sample the corners). Default is auto
                for sprites with "key": true, because Gemini's magenta varies from image to image.
--no-key        do not remove any background (use when the image already has real alpha)
--tolerance N   how far from the key colour still counts as background (default 60, per-channel sum/3)
--colours N     palette size (default: the sprite's "colours" in sprites.json, else max_colours, else 16; 0 = keep all)
--resample      box (default, cleanest), nearest (crispest, can be noisy), lanczos (softest)
--anchor        where the subject sits if it doesn't fill the target: bottom | center
--saturate X    multiply colour saturation after shrinking (e.g. 1.4); bright accents like a lit window get washed out by
                the shrink. Also spec key "saturate".
--brighten X    multiply brightness after shrinking (e.g. 1.25) for sprites that come out too dark. Spec key "brighten".
--tile          treat as a seamless tile: no keying, no cropping, straight resize to the exact size
"""
import argparse, json, sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageEnhance


def pixels(img):
    """Pixel iterator that works on old and new Pillow."""
    return img.get_flattened_data() if hasattr(img, "get_flattened_data") else img.getdata()

ROOT = Path(__file__).resolve().parent.parent
SPEC = Path(__file__).with_name("sprites.json")
RESAMPLE = {"box": Image.BOX, "nearest": Image.NEAREST, "lanczos": Image.LANCZOS}


def parse_colour(s):
    s = s.lstrip("#")
    if len(s) != 6:
        raise ValueError(f"bad colour '{s}', expected #RRGGBB")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def sample_key(img, patch=12):
    """Median colour of the four corner patches. Gemini's 'magenta' varies per image (and JPEG shifts it),
    so measuring it beats trusting #FF00FF."""
    w, h = img.size
    rgb = img.convert("RGB")
    vals = [[], [], []]
    for x0, y0 in ((0, 0), (w - patch, 0), (0, h - patch), (w - patch, h - patch)):
        for y in range(y0, y0 + patch):
            for x in range(x0, x0 + patch):
                for c, v in enumerate(rgb.getpixel((x, y))):
                    vals[c].append(v)
    return tuple(sorted(v)[len(v) // 2] for v in vals)


def remove_background(img, key, tol):
    """Make pixels matching `key` transparent, but only those connected to the image border."""
    w, h = img.size
    px = img.load()

    def match(x, y):
        r, g, b, a = px[x, y]
        return a == 0 or (abs(r - key[0]) + abs(g - key[1]) + abs(b - key[2])) / 3 <= tol

    seen = bytearray(w * h)
    q = deque()
    for x in range(w):
        q.append((x, 0)); q.append((x, h - 1))
    for y in range(h):
        q.append((0, y)); q.append((w - 1, y))
    while q:
        x, y = q.popleft()
        if not (0 <= x < w and 0 <= y < h) or seen[y * w + x]:
            continue
        seen[y * w + x] = 1
        if not match(x, y):
            continue
        px[x, y] = (0, 0, 0, 0)
        q.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    # Remove the pinkish fringe left by anti-aliasing against the key colour.
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a and (abs(r - key[0]) + abs(g - key[1]) + abs(b - key[2])) / 3 <= tol * 0.6:
                # only if touching transparency
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and px[nx, ny][3] == 0:
                        px[x, y] = (0, 0, 0, 0)
                        break
    # Enclosed gaps (e.g. inside a bow) are not reachable from the border, so also clear any pixel that is
    # clearly key-coloured anywhere. Safe because prompts forbid magenta on the subject.
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a and (abs(r - key[0]) + abs(g - key[1]) + abs(b - key[2])) / 3 <= tol * 0.6:
                px[x, y] = (0, 0, 0, 0)
    return img


def quantise(img, colours):
    """Reduce opaque pixels to `colours` colours, leaving alpha untouched."""
    if colours <= 0:
        return img
    r, g, b, a = img.split()
    opaque = [p for p in pixels(img) if p[3]]
    if not opaque:
        return img
    mean = tuple(sum(c[i] for c in opaque) // len(opaque) for i in range(3))
    filler = Image.new("RGB", img.size, mean)
    rgb = Image.composite(img.convert("RGB"), filler, a.point(lambda v: 255 if v else 0))
    q = rgb.quantize(colors=colours, method=Image.MEDIANCUT, dither=Image.NONE).convert("RGB")
    out = q.convert("RGBA")
    out.putalpha(a)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst", nargs="?")
    ap.add_argument("--sprite")
    ap.add_argument("--size")
    ap.add_argument("--key")
    ap.add_argument("--no-key", action="store_true")
    ap.add_argument("--tolerance", type=float, default=60)
    ap.add_argument("--colours", type=int)
    ap.add_argument("--resample", choices=RESAMPLE, default="box")
    ap.add_argument("--anchor", choices=["bottom", "center"])
    ap.add_argument("--tile", action="store_true")
    ap.add_argument("--saturate", type=float)
    ap.add_argument("--brighten", type=float)
    ap.add_argument("--alpha-threshold", type=int, default=110)
    a = ap.parse_args()

    spec, data = {}, {}
    if a.sprite:
        data = json.loads(SPEC.read_text())
        if a.sprite not in data["sprites"]:
            sys.exit(f"unknown sprite '{a.sprite}'. Known: {', '.join(data['sprites'])}")
        spec = data["sprites"][a.sprite]

    size = a.size or (f"{spec['size'][0]}x{spec['size'][1]}" if spec else None)
    if not size:
        sys.exit("need --sprite or --size")
    tw, th = (int(v) for v in size.lower().split("x"))
    dst = Path(a.dst) if a.dst else (ROOT / "assets" / spec["file"] if spec else None)
    if dst is None:
        sys.exit("need an output path or --sprite")
    anchor = a.anchor or spec.get("anchor", "center")
    colours = a.colours if a.colours is not None else spec.get("colours", data.get("max_colours", 16))
    tile = a.tile or spec.get("tile", False)
    key_arg = None
    if not tile and not a.no_key:
        key_arg = a.key or ("auto" if spec.get("key", False) else None)

    img = Image.open(a.src).convert("RGBA")
    print(f"source  {a.src}  {img.width}x{img.height}")

    key = None
    if key_arg == "auto":
        key = sample_key(img)
        print(f"key     auto-detected background #{key[0]:02X}{key[1]:02X}{key[2]:02X}")
    elif key_arg:
        key = parse_colour(key_arg)

    if tile:
        out = img.resize((tw, th), RESAMPLE[a.resample])
        out = quantise(out.convert("RGBA"), colours)
        out.putalpha(255)
    else:
        if key:
            img = remove_background(img, key, a.tolerance)
        bbox = img.getchannel("A").point(lambda v: 255 if v > a.alpha_threshold else 0).getbbox()
        if not bbox:
            sys.exit("nothing left after background removal - check --key / --tolerance")
        img = img.crop(bbox)
        scale = min(tw / img.width, th / img.height)
        nw, nh = max(1, round(img.width * scale)), max(1, round(img.height * scale))
        # Resize colour and alpha separately so edge colour doesn't bleed into transparent pixels.
        rgb = img.convert("RGB")
        alpha = img.getchannel("A")
        # premultiply-ish: replace transparent colour with nearest opaque via blur-free approach (mean fill)
        opaque = [p for p in pixels(img) if p[3] > a.alpha_threshold]
        mean = tuple(sum(c[i] for c in opaque) // len(opaque) for i in range(3))
        rgb = Image.composite(rgb, Image.new("RGB", rgb.size, mean), alpha.point(lambda v: 255 if v > a.alpha_threshold else 0))
        small = rgb.resize((nw, nh), RESAMPLE[a.resample]).convert("RGBA")
        small_a = alpha.resize((nw, nh), RESAMPLE[a.resample]).point(lambda v: 255 if v >= a.alpha_threshold else 0)
        small.putalpha(small_a)
        sat = a.saturate if a.saturate is not None else spec.get("saturate")
        bri = a.brighten if a.brighten is not None else spec.get("brighten")
        if sat or bri:
            sa = small.getchannel("A")
            t = small.convert("RGB")
            if sat:
                t = ImageEnhance.Color(t).enhance(sat)
            if bri:
                t = ImageEnhance.Brightness(t).enhance(bri)
            small = t.convert("RGBA")
            small.putalpha(sa)
        small = quantise(small, colours)
        out = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        ox = (tw - nw) // 2
        oy = th - nh if anchor == "bottom" else (th - nh) // 2
        out.paste(small, (ox, oy))

    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst, optimize=True)
    used = len({p for p in pixels(out) if p[3]})
    print(f"wrote   {dst}  {out.width}x{out.height}  {used} colours  {dst.stat().st_size} bytes")


if __name__ == "__main__":
    main()
