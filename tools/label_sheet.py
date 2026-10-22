"""Label sheets for surplus-run clusters: one row per cluster, BIG crops.

Renders the top-N clusters (by member count) with 3 representative crops
each, zoomed, plus cluster id + size + first members' verse refs, into
/tmp/opencode/label_sheet.png (tiled across pages of 8 rows).

Usage: python tools/label_sheet.py [TOP=60] [PAGES=3]
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mine_surplus import get_page, bands_of, CTX

OUT = Path("/tmp/opencode")


def crop(p, band, x0, x1, zoom=2.4):
    bands = bands_of(p)
    y0, y1, _ = bands[band]
    im = get_page(p)
    ctx = max(CTX, (150 - (x1 - x0)) // 2)
    cx0 = max(0, x0 - ctx)
    cx1 = min(im.width, x1 + ctx)
    c = im.crop((cx0, y0, cx1, y1 + 1))
    c = c.resize((int(c.width * zoom), int(c.height * zoom)), Image.LANCZOS)
    return c


def main():
    top = 60
    npages = 3
    if len(sys.argv) > 1:
        top = int(sys.argv[1])
    if len(sys.argv) > 2:
        npages = int(sys.argv[2])
    runs = json.load(open("tools/data/surplus_runs.json"))
    by_cl = {}
    for r in runs:
        by_cl.setdefault(r["cluster"], []).append(r)
    sizes = sorted(by_cl.items(), key=lambda kv: -len(kv[1]))[:top]
    CW, CH = 660, 200
    COLS = 2
    ROWS = 9
    page = 0
    for start in range(0, len(sizes), ROWS * COLS):
        chunk = sizes[start:start + ROWS * COLS]
        sheet = Image.new("RGB", (COLS * CW, ROWS * CH), (255, 255, 255))
        dr = ImageDraw.Draw(sheet)
        for k, (cid, members) in enumerate(chunk):
            gx, gy = (k % COLS) * CW, (k // COLS) * CH
            dr.text((gx + 6, gy + 4),
                    f"CL{cid} n={len(members)} " +
                    ",".join(m['verses'] for m in members[:3]),
                    fill=(0, 0, 0))
            for j, r in enumerate(members[:2]):
                c = crop(r["page"], r["band"], r["x0"], r["x1"])
                sc = min(310 / c.width, 168 / c.height, 2.4)
                if sc > 1:
                    c = c.resize((int(c.width * sc), int(c.height * sc)),
                                 Image.LANCZOS)
                dr.text((gx + 6 + j * 324, gy + 18),
                        f"p{r['page']} b{r['band']}", fill=(120, 0, 0))
                sheet.paste(c, (gx + 6 + j * 324, gy + 36))
        OUT.mkdir(parents=True, exist_ok=True)
        sheet.save(OUT / f"label_sheet_{page}.png")
        print(f"label_sheet_{page}.png ({len(chunk)} clusters)")
        page += 1
        if page >= npages:
            break


if __name__ == "__main__":
    main()
