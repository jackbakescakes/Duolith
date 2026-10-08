# Duolith

A mage and a living stone tower, each levelling the other. Prototype of the full day/night loop in plain HTML + canvas, to prove it's fun before a likely Godot rebuild.

Right now there are two phases, switched by hand with **N** (temporary, for testing):

- **Night** (zoomed out): steer the slowly-walking tower with WASD, zombies swarm in from every side, the tower auto-fires an arrow every 2 seconds at the nearest one, and dead zombies leave XP gems on the ground. Each night starts a bit busier, and the tower wakes at full health.
- **Day** (camera zooms in 4x on the mage): the tower roots where it stopped. Walk with WASD; the mage always faces the mouse. Click (or hold) near a tree to chop wood, or near a rock to mine stone, with an 18% chance of copper and a 5% chance of iron per rock. Walk over the night's XP gems to collect them; a blue marker at the screen edge points to the nearest one off screen. Trees and rocks are topped up around the tower each dawn.

A resource counter (wood, stone, copper, iron, XP) sits at the bottom of the screen. Nothing spends resources yet.

## Layout

```
index.html          game logic only. No images, no base64.
assets/             all art, as image files loaded by URL at runtime
  tower/ mage/ enemies/ resources/ pickups/ projectiles/ tiles/ ui/
art-src/            raw Gemini downloads (git-ignored; ~0.5 MB each)
tools/
  sprites.json      single source of truth: every sprite's file, pixel size, palette, anchor, description
  prompt.py         prints the Gemini prompt for a sprite
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

The browser console lists any sprites still using placeholders.

## Art pipeline

1. **Prompt.** `python3 tools/prompt.py zombie` prints a Gemini prompt (flat magenta background by default).
2. **Generate** in Gemini, download the image (it arrives as a JPEG), save it as `art-src/zombie.jpg`.
3. **Downscale.** `python3 tools/downscale.py art-src/zombie.jpg --sprite zombie`
   auto-detects and removes the background colour, crops to the subject, shrinks to the exact size from `sprites.json`,
   snaps alpha to on/off, reduces the palette, and writes `assets/enemies/zombie.png`.
4. **Check.** `python3 tools/check_assets.py`
5. **Play.** Refresh the page. No code change needed for the existing sprites.

Requires Python 3 and Pillow (`pip install pillow`).

Notes from the first run:

- **Prompt wording matters.** Asking Gemini for an "exact 12x12 pixel grid" made it answer with a text grid instead of a picture.
  `prompt.py` now asks for "an actual picture, chunky visible square pixels" and leaves the exact size to `downscale.py`.
- **Why magenta, not "transparent".** Image models usually return an opaque image even when asked for transparency.
  A flat key colour is reliable to remove, and Gemini's magenta differs from image to image (and JPEG shifts it),
  so `downscale.py` samples the corners instead of trusting `#FF00FF`.
- **Size vs detail.** Detailed Gemini art needs room: the zombie was an unreadable blob at 12x12 and reads well at 20x20.
  Tiny details (the tower's lit window) vanish when shrunk, so prompt for them large and bold.
- If a result looks mushy, try `--resample nearest`, a different `--colours`, or regenerate.

## Adding a sprite

1. Add an entry to `tools/sprites.json` (file, size, anchor, description; optional `colours`).
2. Add the same key and path to `ASSET_FILES` in `index.html`, and draw it with `drawSprite()` plus a placeholder fallback.
3. `python3 tools/check_assets.py` fails if the two disagree.

## Later: sprite atlas

Once there are many sprites and animation frames, pack them into one image plus a small JSON of frame rects, and load that
single file instead of one request per sprite. Keep `sprites.json` as the source and generate the atlas from `assets/`,
so the per-sprite files stay the editable truth. Not needed yet (all current sprites total about 4 KB).

## Sprite sizes (current)

| sprite | size | note |
|---|---|---|
| tower | 40x48 | bottom-anchored, 24-colour palette. Hitbox in code is 28x40 |
| zombie | 20x20 | bottom-anchored, faces right (flipped in code when walking left). Hitbox 12 |
| xp | 8x8 | |
| arrow | 12x4 | drawn pointing right, rotated in code |
| ground | 16x16 | seamless tile |
| mage | 12x16 | not drawn yet (placeholder). Bottom-anchored, faces right, flipped toward the mouse. Staff is drawn in code |
| tree | 16x20 | not drawn yet (placeholder). Bottom-anchored |
| rock | 12x8 | not drawn yet (placeholder). Bottom-anchored |

## Planned

- Spending: wood/stone/copper/iron buy tower upgrades (attacks, defences); XP buys mage upgrades.
- A real day/night clock to replace the N key, with the mage's morning as a timed scramble.
- The zoom-out wake-up cutscene (the tower yawns, stretches and pulls its root-legs out of the ground,
  which needs an awake tower with a face).
