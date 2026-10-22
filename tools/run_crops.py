"""Crop sheets for lit_verdict page claims: every colored run on a page,
cropped with line context, zoomed, labeled (kind band x0-x1). One sheet
per page -> /tmp/opencode/lit_crops/sheet_<page>.png. Read visually to
assign word identities (ink-first; token boxes not trusted for x).

Usage: python tools/run_crops.py 181 194 62 63 ...
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rebuild_runs import page_bands
from lit_verdict import MJ

OUT = Path("/tmp/opencode/lit_crops")
PICS = Path(__file__).resolve().parent.parent / "hayrat-pics"


def sheet(p):
    bands = page_bands(p)
    if bands is None:
        print(p, "no bands")
        return
    seen, runs = set(), []
    for s in MJ["segments"]:
        if s["page"] != p:
            continue
        for r in s.get("runs", []):
            key = (r["kind"], r["band"], round(r["x0"], 1), round(r["x1"], 1))
            if key in seen or r["band"] >= len(bands):
                continue
            seen.add(key)
            runs.append(r)
    runs.sort(key=lambda r: (r["band"], r["x0"]))
    im = Image.open(PICS / f"page_{p}.png").convert("RGB")
    Z = 3
    pad_y = 14
    strips = []
    for r in runs:
        y0, y1, _ = bands[r["band"]]
        crop = im.crop((max(0, int(r["x0"]) - 70), y0 - pad_y,
                        min(im.width, int(r["x1"]) + 70), y1 + pad_y))
        crop = crop.resize((crop.width * Z, crop.height * Z), Image.LANCZOS)
        strips.append((r, crop))
    W = max(c.width for _, c in strips) + 320
    H = sum(c.height + 10 for _, c in strips) + 10
    out = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(out)
    y = 5
    for r, c in strips:
        dr.text((5, y + c.height // 2 - 6),
                f"{r['kind']} b{r['band']} x{round(r['x0'])}-{round(r['x1'])}",
                fill="black")
        out.paste(c, (300, y))
        dr.line([(295, y), (295, y + c.height)], fill="red", width=2)
        y += c.height + 10
    OUT.mkdir(parents=True, exist_ok=True)
    out.save(OUT / f"sheet_{p}.png")
    print(p, len(runs), "runs ->", OUT / f"sheet_{p}.png")


def main():
    for a in sys.argv[1:]:
        sheet(int(a))


if __name__ == "__main__":
    main()
