#!/usr/bin/env python3
"""Annotate detected colored words onto mushaf pages and build pair montages.

Usage:
    .venv/bin/python tools/annotate.py 422 [82 83 540 541 ...]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from page_scan import (PICS, classify, cluster_1d, components, detect_words,
                       dilate, load_page, merge_words)

OUT = Path("/tmp/opencode")


def detect(n):
    a, bands, blk, comps = detect_words(n)
    return a, [c for c in comps if not c["ornament"]]


def dilate_mask(mask, k=6):
    return dilate(mask, k)


def annotate_page(n):
    a, comps = detect(n)
    im = Image.fromarray(a.astype(np.uint8))
    d = ImageDraw.Draw(im)
    for c in comps:
        col = {"red": (0, 130, 255), "pink": (0, 200, 0), "green": (255, 0, 255),
               "gold": (255, 140, 0), "orange": (255, 140, 0), "blue": (0, 200, 200),
               "other": (128, 128, 128)}[c["color"]]
        d.rectangle([c["x0"] - 4, c["y0"] - 4, c["x1"] + 4, c["y1"] + 4], outline=col, width=3)
        d.text((c["x0"], max(0, c["y0"] - 22)), f"L{c.get('line', '?')}", fill=col)
    out = OUT / f"ann_{n}.png"
    im.save(out)
    reds = [c for c in comps if c["color"] == "red"]
    print(f"page {n}: red={len(reds)} total={len(comps)} -> {out}")
    return im


def main():
    nums = [int(x) for x in sys.argv[1:]]
    ims = {n: annotate_page(n) for n in nums}
    # side-by-side for consecutive pairs found in the list
    done = set()
    for n in nums:
        for m in nums:
            if m == n + 1 and (n, m) not in done:
                w = max(ims[n].width, ims[m].width)
                h = max(ims[n].height, ims[m].height)
                canvas = Image.new("RGB", (w * 2 + 20, h), (255, 255, 255))
                canvas.paste(ims[n], (0, 0))
                canvas.paste(ims[m], (w + 20, 0))
                canvas.save(OUT / f"pair_{n}_{m}.png")
                print(f"pair {n}|{m} -> {OUT}/pair_{n}_{m}.png")
                done.add((n, m))


if __name__ == "__main__":
    main()
