"""Build atlas sheets of sign marks for visual reading.

Groups sign_catalog blobs by (ink, w-bucket, h-bucket), samples up to N
crops per class at high zoom, tiles into sheets under /tmp/opencode/sign_atlas.
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
PICS = ROOT.parent / "hayrat-pics"
OUT = Path("/tmp/opencode/sign_atlas")
WB = [(3, 7), (7, 12), (12, 20), (20, 32), (32, 55), (55, 90)]
HB = [(4, 7), (7, 10), (10, 14), (14, 22), (22, 40)]


def bucket(v, bs):
    for lo, hi in bs:
        if lo <= v < hi:
            return (lo, hi)
    return bs[-1]


def main():
    S = json.load(open(ROOT / "data" / "sign_catalog.json"))
    OUT.mkdir(parents=True, exist_ok=True)
    classes = defaultdict(list)
    for i, s in enumerate(S):
        wb = bucket(s["w"], WB)
        hb = bucket(s["h"], HB)
        classes[(s["ink"], wb, hb)].append(i)
    rng = np.random.default_rng(3)
    for key, idxs in sorted(classes.items(), key=lambda kv: str(kv[0])):
        if len(idxs) < 6:
            continue
        idxs = rng.permutation(idxs)[:16]
        cells = []
        for i in idxs:
            s = S[i]
            im = Image.open(PICS / f"page_{s['pg']}.png").convert("RGB")
            pad = 6
            c = im.crop((max(0, s["x0"] - pad), max(0, s["y0"] - pad),
                         s["x1"] + pad, s["y1"] + pad))
            z = 8
            c = c.resize((c.width * z, c.height * z), Image.LANCZOS)
            cells.append((c, f"p{s['pg']} y{s['y0']} x{s['x0']}-{s['x1']}"))
        cw = 340
        rows = (len(cells) + 3) // 4
        ch = 260
        sheet = Image.new("RGB", (4 * cw, rows * ch), (250, 250, 250))
        dr = ImageDraw.Draw(sheet)
        for k, (c, tag) in enumerate(cells):
            gx, gy = (k % 4) * cw, (k // 4) * ch
            if c.width > cw - 8 or c.height > ch - 26:
                sc = min((cw - 8) / c.width, (ch - 26) / c.height)
                c = c.resize((max(1, int(c.width * sc)), max(1, int(c.height * sc))))
            dr.text((gx + 4, gy + 4), tag, fill=(0, 0, 0))
            sheet.paste(c, (gx + 4, gy + 22))
        name = f"{key[0]}_w{key[1][0]}-{key[1][1]}_h{key[2][0]}-{key[2][1]}.png"
        sheet.save(OUT / name)
        print(name, len(idxs), "of", len(classes[key]))


if __name__ == "__main__":
    main()