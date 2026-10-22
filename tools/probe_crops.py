import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path('.')

meta, lab = np.load('tools/data/red_feats.npz')['meta'], np.load('tools/data/red_feats.npz')['lab']
Bs = np.load('/tmp/opencode/ink_B.npy')
PICS = Path('hayrat-pics')
DATA = Path('tools/data/real_boxes')
OUT = Path('/tmp/opencode/cluster_sheets')
ims = {}
pages = {}

def get_page(n):
    if n not in ims:
        ims[n] = Image.open(PICS / f'page_{n}.png').convert('RGB')
    return ims[n]

def get_json(n):
    if n not in pages:
        pages[n] = json.loads((DATA / f'page_{n:03d}.json').read_text())
    return pages[n]

def crop_around(i, padx, pady, scale=2):
    pg, jj = int(meta[i, 0]), int(meta[i, 1])
    r = get_json(pg)['reds'][jj]
    x0, y0, x1, y1 = r['x0'], r['y0'], r['x1'], r['y1']
    im = get_page(pg)
    c = im.crop((max(0, x0 - padx), max(0, y0 - pady),
                 min(im.width, x1 + padx), min(im.height, y1 + pady)))
    return c.resize((c.width * scale, c.height * scale), Image.LANCZOS), f'i{i} p{pg}:{jj} B={Bs[i]:.0f} w={r["w"]} h={r["h"]}'


def sheet(name, idxs, padx, pady, cols=2, cw=740, ch=230):
    cells = []
    for i in idxs:
        try:
            cells.append(crop_around(i, padx, pady))
        except Exception as e:
            print('skip', i, e)
    rows = (len(cells) + cols - 1) // cols
    s = Image.new('RGB', (cols * cw, rows * ch), (255, 255, 255))
    dr = ImageDraw.Draw(s)
    for k, (im, tag) in enumerate(cells):
        gx, gy = (k % cols) * cw, (k // cols) * ch
        if im.width > cw or im.height > ch - 20:
            sc = min(cw / im.width, (ch - 20) / im.height)
            im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))))
        s.paste(im, (gx + (cw - im.width) // 2, gy + 20))
        dr.text((gx + 6, gy + 4), tag, fill=(0, 0, 0))
    s.save(OUT / name)
    print('->', OUT / name)

rng = np.random.default_rng(11)

# 1. الله (c7, deep): is there a magenta sign above?
c7d = [i for i in np.where(lab == 7)[0] if Bs[i] < 90]
sheet('q1_allah_sign.png', list(rng.choice(c7d, 6, replace=False)), 60, 45, cols=3, cw=500, ch=200)

# 2. c3 small marks: deep vs magenta
c3 = np.where(lab == 3)[0]
c3d = [i for i in c3 if Bs[i] < 90]
c3m = [i for i in c3 if Bs[i] >= 90]
sheet('q2a_c3_deep.png', list(rng.choice(c3d, 6, replace=False)), 130, 40, cols=2)
sheet('q2b_c3_mag.png', list(rng.choice(c3m, 6, replace=False)), 130, 40, cols=2)

# 3. c1 magenta members
c1 = np.where(lab == 1)[0]
c1m = [i for i in c1 if Bs[i] >= 90]
sheet('q3_c1_mag.png', list(rng.choice(c1m, 8, replace=False)), 100, 30, cols=2)

# 4. c10 magenta members
c10 = np.where(lab == 10)[0]
c10m = [i for i in c10 if Bs[i] >= 90]
sheet('q4_c10_mag.png', list(rng.choice(c10m, 8, replace=False)), 100, 30, cols=2)

# 5. c1 deep members (composite check)
c1d = [i for i in c1 if Bs[i] < 90]
sheet('q5_c1_deep.png', list(rng.choice(c1d, 8, replace=False)), 100, 30, cols=2)