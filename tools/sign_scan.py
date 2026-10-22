"""Scan all pages for interline/margin sign marks (magenta + deep-red ink blobs).

Signs = reddish-ink blobs that sit OUTSIDE the black-text word rows
(interline gaps, top/bottom margins), excluding full-width strips and
in-text colored words. Output: tools/data/sign_catalog.json
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
PICS = ROOT.parent / "hayrat-pics"
OUT = ROOT / "data" / "sign_catalog.json"


def page_masks(im):
    a = np.asarray(im).astype(np.int16)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    dark = (R < 120) & (G < 120) & (B < 150)
    redish = (R - G > 45) & (R > 120)
    crim = redish & (B < 108)
    mag = redish & (B >= 108)
    return dark, crim, mag


def row_groups(rows, gap=6):
    groups = []
    if len(rows) == 0:
        return groups
    s = p = rows[0]
    for y in rows[1:]:
        if y - p > gap:
            groups.append((s, p))
            s = y
        p = y
    groups.append((s, p))
    return groups


def blob_spans(mask, y0, y1, minpx=3, gapx=10):
    colsum = mask[y0:y1].sum(axis=0)
    xs = np.where(colsum >= minpx)[0]
    if len(xs) == 0:
        return []
    out = []
    st = pr = xs[0]
    for x in xs[1:]:
        if x - pr > gapx:
            out.append((int(st), int(pr)))
            st = x
        pr = x
    out.append((int(st), int(pr)))
    return out


def main():
    signs = []
    for pg in range(1, 605):
        im = Image.open(PICS / f"page_{pg}.png").convert("RGB")
        dark, crim, mag = page_masks(im)
        H = im.height
        # black text rows: rows with >=25 dark px
        darkrows = np.where(dark.sum(axis=1) >= 25)[0]
        text_groups = row_groups(darkrows, gap=8)
        # text-line rows = groups with height>=25 (word rows); headers/cartouches too
        word_rows = [(a, b) for a, b in text_groups if b - a >= 22]
        if not word_rows:
            continue
        # gap mask: rows not within any word row (pad 2)
        gapmask = np.ones(H, dtype=bool)
        for a, b in word_rows:
            gapmask[max(0, a - 2):b + 3] = False
        # signs: reddish px in gap rows, grouped by y
        reddish = crim | mag
        redrows = np.where((reddish & gapmask[:, None]).sum(axis=1) >= 6)[0]
        for a, b in row_groups(redrows, gap=8):
            h = b - a + 1
            if h < 4 or h > 40:
                continue
            seg_c = blob_spans(crim, a, b + 1)
            seg_m = blob_spans(mag, a, b + 1)
            # keep blobs < 90px wide (strips are 300+)
            for ink, spans in (("crim", seg_c), ("mag", seg_m)):
                for x0, x1 in spans:
                    w = x1 - x0 + 1
                    if w < 3 or w > 90:
                        continue
                    npx = int(reddish[a:b + 1, x0:x1 + 1].sum())
                    if npx < 12:
                        continue
                    signs.append(dict(pg=pg, y0=int(a), y1=int(b), h=int(h),
                                      x0=x0, x1=x1, w=int(w), ink=ink, npx=npx))
    OUT.write_text(json.dumps(signs))
    print("signs:", len(signs), "pages:", len(set(s["pg"] for s in signs)))


if __name__ == "__main__":
    main()