"""Build assets/smith/smith.png (the blacksmith animation atlas) from the Gemini sheets in art-src/smith/.

Layout: one animation per row, FW x FH frames, left to right. ROWS below is the contract with index.html.
Run from the repo root:  python3 tools/build_smith.py [--preview]
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from smith_lib import *
import cv2

FW = FH = 56
BASE_Y = FH - 4            # feet baseline inside a frame
CX = FW // 2
WIN = 448                  # source pixels covered by one frame (=> scale 56/448 = 0.125; the 264px smith becomes ~33px)
SNAP = 12                  # source px: bottoms this close to the sheet baseline are treated as grounded

# name -> (source sheet, frame count, mode, flip, reverse, frame picks)
#   mode 'ground': snap feet to the baseline; 'abs': keep the sheet's own vertical position (jump / death)
ROWS = [
    ('idle_down',   'idle',       6, 'ground', False, False, [0, 1]),
    ('idle_side',   'walk_side',  6, 'ground', False, False, [2, 5]),
    ('idle_up',     'idle',       6, 'ground', False, False, [4, 5]),
    ('walk_side',   'walk_side',  6, 'ground', False, False, None),
    ('walk_down',   'walk_down',  6, 'ground', False, False, None),
    ('walk_up',     'walk_up',    6, 'ground', False, False, None),
    ('mine',        'mine',       6, 'ground', False, False, None),
    ('chop',        'chop2',      5, 'ground', False, False, [0, 1, 2, 3, 1]),
    ('draw_axe',    'draw_axe',   6, 'ground', False, False, None),
    ('draw_pick',   'draw_pick',  6, 'ground', False, False, None),
    ('draw_sword',  'draw_sword', 6, 'ground', False, False, None),
    ('slash',       'slash1',     6, 'ground', False, False, None),
    ('hurt',        'hurt',       4, 'ground', False, False, None),
    ('death',       'death',      6, 'abs',    False, False, None),
    ('jump',        'jump',       6, 'abs',    False, False, None),
    ('walk_axe',    'walk_axe',   6, 'ground', False, False, [0, 2, 3, 5]),
    ('walk_pick',   'walk_pick',  6, 'ground', False, False, None),
    ('walk_sword',  'walk_sword', 6, 'ground', False, False, [0, 2, 3, 5]),
    ('hammer',      'hammer',     6, 'ground', False, False, None),
    ('cheer',       'cheer',      6, 'ground', False, False, None),
]
MAXC = 8

def render_frame(arr, lab, g, base_src, dy_src):
    x0, y0, x1, y1, ids = g
    sub, _ = crop_group(arr, lab, g)
    cx = x0 + body_core(sub)
    ay = base_src + dy_src                       # source y that maps to BASE_Y
    sx0, sy0 = int(round(cx - WIN / 2)), int(round(ay - BASE_Y * WIN / FH))
    canvas = np.zeros((WIN, WIN, 4), np.float32)
    full = np.zeros_like(arr)
    full[y0:y1, x0:x1] = sub
    for yy in range(WIN):
        pass
    # copy the window (clipped to the sheet)
    H, W = arr.shape[:2]
    cx0, cy0 = max(sx0, 0), max(sy0, 0); cx1, cy1 = min(sx0 + WIN, W), min(sy0 + WIN, H)
    canvas[cy0 - sy0: cy1 - sy0, cx0 - sx0: cx1 - sx0] = full[cy0:cy1, cx0:cx1]
    a = (canvas[..., 3:4] > 110).astype(np.float32)
    pm = np.concatenate([canvas[..., :3] * a, a], -1)
    small = cv2.resize(pm, (FW, FH), interpolation=cv2.INTER_AREA)
    al = small[..., 3:4]
    rgb = np.where(al > 0.01, small[..., :3] / np.maximum(al, 1e-3), 0)
    out = np.concatenate([rgb, (al >= 0.5) * 255.0], -1).clip(0, 255).astype(np.uint8)
    return out

def main():
    frames = {}
    for name, sheet, n, mode, flip, rev, picks in ROWS:
        if not os.path.exists(os.path.join(SRC, sheet + '.jpg')):
            print('skip', name, '(no', sheet + '.jpg)'); continue
        arr = load_keyed(sheet)
        groups, lab = frame_groups(arr, n, minpx=700)
        assert len(groups) == n, (name, len(groups))
        bottoms = [g[3] for g in groups]
        base = int(np.median(bottoms))
        out = []
        for i, g in enumerate(groups):
            dy = 0
            if mode == 'abs' or abs(g[3] - base) > SNAP:
                dy = g[3] - base if mode == 'abs' else (g[3] - base)
            if mode == 'ground' and abs(g[3] - base) <= SNAP: dy = 0
            out.append(render_frame(arr, lab, g, base, dy))
        if picks is not None: out = [out[i] for i in picks]
        frames[name] = out
        print(name, len(out), 'frames; base', base)
    rows = [r[0] for r in ROWS if r[0] in frames]
    atlas = np.zeros((len(ROWS) * FH, MAXC * FW, 4), np.uint8)
    meta = {'fw': FW, 'fh': FH, 'base': BASE_Y, 'anims': {}}
    for ri, (name, *_rest) in enumerate(ROWS):
        meta['anims'][name] = {'row': ri, 'n': len(frames.get(name, []))}
        for fi, f in enumerate(frames.get(name, [])):
            atlas[ri * FH:(ri + 1) * FH, fi * FW:(fi + 1) * FW] = f
    img = Image.fromarray(atlas, 'RGBA')
    img = d.quantise(img, 64)
    # hard alpha
    a = img.getchannel('A').point(lambda v: 255 if v >= 128 else 0); img.putalpha(a)
    os.makedirs('assets/smith', exist_ok=True)
    img.save('assets/smith/smith_atlas.png', optimize=True)
    json.dump(meta, open('assets/smith/smith_atlas.json', 'w'))
    print('saved', img.size, os.path.getsize('assets/smith/smith_atlas.png'), 'bytes')
    if '--preview' in sys.argv:
        bg = Image.new('RGBA', img.size, (70, 110, 60, 255)); bg.alpha_composite(img)
        bg.resize((img.width * 3, img.height * 3), Image.NEAREST).save(os.environ.get('PREVIEW', '/tmp/smith_preview.png'))

main()
