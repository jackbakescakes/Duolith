"""Helpers for turning Gemini's smith animation sheets (one row of frames on magenta) into game frames."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from PIL import Image
from scipy import ndimage
import downscale as d

SRC = os.path.join(os.path.dirname(__file__), '..', 'art-src', 'smith')

def load_keyed(name, tol=60):
    """Sheet -> RGBA array with the magenta removed (cached, the flood fill is slow in pure python)."""
    cache = os.path.join(SRC, 'cache', name + '.png')
    if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(os.path.join(SRC, name + '.jpg')):
        return np.array(Image.open(cache).convert('RGBA'))
    img = Image.open(os.path.join(SRC, name + '.jpg')).convert('RGBA')
    k = d.remove_background(img, d.sample_key(img), tol)
    k.save(cache)
    return np.array(k)

def frame_groups(arr, n, minpx=150):
    """Connected blobs -> exactly n frame groups (left to right) by merging the closest neighbours."""
    a = arr[..., 3] > 110
    lab, cnt = ndimage.label(a, structure=np.ones((3, 3)))
    sizes = ndimage.sum(a, lab, range(1, cnt + 1))
    objs = ndimage.find_objects(lab)
    groups = []
    for i, (sl, sz) in enumerate(zip(objs, sizes), start=1):
        if sz < minpx: continue
        groups.append([sl[1].start, sl[0].start, sl[1].stop, sl[0].stop, {i}])
    groups.sort(key=lambda g: (g[0] + g[2]) / 2)
    while len(groups) > n:
        best, bi = 1e9, 0
        for i in range(len(groups) - 1):
            gap = groups[i + 1][0] - groups[i][2]
            if gap < best: best, bi = gap, i
        g, h = groups[bi], groups.pop(bi + 1)
        groups[bi] = [min(g[0], h[0]), min(g[1], h[1]), max(g[2], h[2]), max(g[3], h[3]), g[4] | h[4]]
    # Two frames whose art touches become one blob: split the widest group at its emptiest column.
    nxt = int(lab.max()) + 1
    while len(groups) < n:
        gi = max(range(len(groups)), key=lambda i: groups[i][2] - groups[i][0])
        x0, y0, x1, y1, ids = groups[gi]
        mask = np.isin(lab[y0:y1, x0:x1], list(ids))
        col = mask.sum(0)
        lo, hi = int(len(col) * 0.3), int(len(col) * 0.7)
        cut = lo + int(np.argmin(col[lo:hi]))
        left = mask.copy(); left[:, cut:] = False
        right = mask & ~left
        sub = lab[y0:y1, x0:x1]
        sub[right] = nxt
        def bb(m, xo):
            ys, xs = np.where(m)
            return [x0 + xs.min(), y0 + ys.min(), x0 + xs.max() + 1, y0 + ys.max() + 1]
        a = bb(left, 0); b = bb(right, 0)
        sub[left] = nxt + 1
        groups[gi:gi + 1] = [a + [{nxt + 1}], b + [{nxt}]]
        nxt += 2
    return groups, lab

def crop_group(arr, lab, g, pad=0):
    x0, y0, x1, y1, ids = g
    sub = arr[y0:y1, x0:x1].copy()
    keep = np.isin(lab[y0:y1, x0:x1], list(ids))
    # Drop stray specks (other frames' bits / small blobs) that are not part of this group
    sub[~keep & (sub[..., 3] > 0)] = 0
    return sub, (x0, y0, x1, y1)

def head_width(sub):
    """Width of the widest row in the top 14% of the opaque area (the bald head), in source pixels."""
    a = sub[..., 3] > 110
    ys = np.where(a.any(1))[0]
    top, bot = ys[0], ys[-1]
    band = a[top: top + max(8, int((bot - top) * 0.14))]
    return int(band.sum(1).max())

def body_core(sub):
    """x-range of the thick middle of the body, ignoring thin tools. Returns centre x in sub coords."""
    a = sub[..., 3] > 110
    col = a.sum(0)
    thick = np.where(col >= col.max() * 0.35)[0]
    return (thick[0] + thick[-1]) / 2
