# Duolith

A mage and a living stone tower, each levelling the other. Prototype of the full day/night loop in plain HTML + canvas, to prove it's fun before a likely Godot rebuild.

## Layout

```
index.html          game logic only. No images, no base64.
assets/             all art, as image files loaded by URL at runtime
  tower/ enemies/ pickups/ projectiles/ tiles/ ui/
art-src/            raw Gemini output (git-ignored; large)
tools/
  sprites.json      single source of truth: every sprite's file, pixel size, anchor, description
  prompt.py         prints the exact Gemini prompt for a sprite
  downscale.py      big Gemini image -> clean tiny pixel-art PNG in assets/
  check_assets.py   lists present/missing sprites, checks sizes, checks index.html matches sprites.json
```

Code and art never mix: the HTML references art only by filename (`ASSET_FILES` near the top of the script).
If a file is missing or fails to load, that sprite keeps its coloured-rectangle placeholder, so the game always runs.

## Running

Opening `index.html` directly works. If your browser blocks local image loads, serve the folder:

```
python3 -m http.server 8000     # then open http://localhost:8000
```

Open the browser console: it lists any sprites still using placeholders.

## Art pipeline

1. **Prompt.** `python3 tools/prompt.py zombie` prints a prompt with the exact target pixel size and a flat magenta
   background (`--transparent` asks for real alpha instead; see note below).
2. **Generate** in Gemini. Save the result as `art-src/zombie.png`.
3. **Downscale.** `python3 tools/downscale.py art-src/zombie.png --sprite zombie`
   removes the magenta, crops to the subject, shrinks to the exact size, snaps alpha to on/off, reduces to 16 colours,
   and writes `assets/enemies/zombie.png`.
4. **Check.** `python3 tools/check_assets.py`
5. **Play.** Refresh the page. No code change needed for the five existing sprites.

Requires Python 3 and Pillow (`pip install pillow`).

**Why magenta instead of "transparent":** image models usually return an opaque image even when asked for a
transparent background (often a painted checkerboard). A flat key colour is reliable to remove. If a particular
Gemini output does come back with real alpha, use `--transparent` in step 1 and `--no-key` in step 3.

If a result looks mushy, try `--resample nearest`, fewer colours (`--colours 12`), or regenerate: prompts that ask for a
chunky pixel grid usually downscale much better than detailed illustrations.

## Adding a sprite

1. Add an entry to `tools/sprites.json` (file, size, anchor, desc).
2. Add the same key and path to `ASSET_FILES` in `index.html`, and draw it with `drawSprite()` plus a placeholder fallback.
3. `python3 tools/check_assets.py` fails if the two disagree.

## Later: sprite atlas

Once there are many sprites and animation frames, pack them into one image plus a small JSON of frame rects, and load that
single file instead of one request per sprite. Keep `sprites.json` as the source and generate the atlas from `assets/`,
so the per-sprite files stay the editable truth. Not needed yet.

## Sprite sizes (current)

| sprite | size | note |
|---|---|---|
| tower | 24x32 | bottom-anchored |
| zombie | 12x12 | bottom-anchored, faces right (flipped in code when walking left) |
| xp | 8x8 | |
| arrow | 12x4 | drawn pointing right, rotated in code |
| ground | 16x16 | seamless tile |
