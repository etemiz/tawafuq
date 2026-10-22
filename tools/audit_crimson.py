"""Crimson-anchor audit of token_map2.

For every divine-name token (الله/لله/رب/ربنا/ربهم...) with a boxed record,
check whether a crimson ink run (B<108 divine ink) actually intersects the
record's y-band on its page near the record's x-range. Tokens whose record
misses all nearby crimson runs are MISALIGNED (line-shift corruption).

Crimson ink legend: crimson = redish & B<108, redish = R-G>45 & R>120.
"""
import json
import sys
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_tokens as mt

DATA = Path(__file__).resolve().parent / "data"
PICS = Path(__file__).resolve().parent.parent / "hayrat-pics"
NAMES = {"الله", "لله", "رب", "ربنا", "ربكم", "ربهم", "ربك", "ربه", "ربي"}


def crimson_runs(page, lo, hi):
    f = PICS / f"page_{page}.png"
    from image_io import open_rgb
    band = np.asarray(open_rgb(f))[lo:hi, :, :]
    r, g, b = band[..., 0].astype(int), band[..., 1].astype(int), band[..., 2].astype(int)
    redish = (r - g > 45) & (r > 120)
    cri = redish & (b < 108)
    ccol = cri.sum(axis=0)
    runs = []
    x = 0
    W = band.shape[1]
    while x < W:
        if ccol[x] >= 2:
            x0 = x
            gap = 0
            while x < W:
                if ccol[x] >= 1:
                    gap = 0
                else:
                    gap += 1
                    if gap > 14:
                        break
                x += 1
            runs.append((x0, x - gap))
        else:
            x += 1
    return runs


def main():
    verses = mt.load_tokens()
    flat = [(s, a, tok) for s, a, ts in verses for tok in ts]
    tm = json.loads((DATA / "token_map2.json").read_text())
    recs = [r for r in tm["map"] if not r.get("skip") and r.get("y")]
    cache = {}
    ok = miss = nocrimson = 0
    bad_pages = Counter()
    bad_list = []
    for r in recs:
        t = r["t"]
        s, a, tok = flat[t]
        if tok not in NAMES:
            continue
        page = r["page"]
        y0, y1 = r["y"]
        if page not in cache:
            cache[page] = {}
        band = cache[page]
        key = (y0 - 60) // 100
        if key not in band:
            band[key] = crimson_runs(page, max(0, y0 - 60), min(1680, y1 + 60))
        runs = band[key]
        if not runs:
            nocrimson += 1
            continue
        rx0, rx1 = r["x"]
        hit = any(min(rx1, c1) - max(rx0, c0) >= 0.3 * (rx1 - rx0)
                  and not (c1 < rx0 or c0 > rx1) for c0, c1 in runs)
        if hit:
            ok += 1
        else:
            miss += 1
            bad_pages[page] += 1
            if len(bad_list) < 40:
                bad_list.append((page, f"{s}:{a}", tok, r["x"], r["y"],
                                 sorted(runs, key=lambda c: -abs((c[0] + c[1]) / 2 - (rx0 + rx1) / 2))[:1]))
    print(f"divine-name records audited: ok={ok} MISALIGNED={miss} "
          f"(no-crimson-on-page={nocrimson})")
    print("worst pages:", bad_pages.most_common(15))
    for b in bad_list[:25]:
        print("  MISS", b)


if __name__ == "__main__":
    main()
