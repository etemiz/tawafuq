"""One tall reading sheet per surplus cluster: BIG crops, stacked.

Usage: python tools/cluster_read.py CL1 [CL2 ...] [--n 4] [--zoom 3]
Output: /tmp/opencode/cl_read/CL{id}.png
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from label_sheet import crop
from PIL import Image

OUT = Path("/tmp/opencode/cl_read")


def main():
    n = 4
    zoom = 3.0
    args = sys.argv[1:]
    if "--n" in args:
        n = int(args[args.index("--n") + 1])
    if "--zoom" in args:
        zoom = float(args[args.index("--zoom") + 1])
    ids = [int(a) for a in args if not a.startswith("--") and
           not a.lstrip("-").isdigit()]
    if args and args[0].lstrip("-").isdigit():
        ids = [int(a) for a in args if a.lstrip("-").isdigit()]
    runs = json.load(open("tools/data/surplus_runs.json"))
    by_cl = {}
    for r in runs:
        by_cl.setdefault(r["cluster"], []).append(r)
    OUT.mkdir(parents=True, exist_ok=True)
    for cid in ids:
        members = by_cl.get(cid, [])
        cells = []
        for r in members[:n]:
            c = crop(r["page"], r["band"], r["x0"], r["x1"], zoom=zoom)
            cells.append((c, f"p{r['page']} b{r['band']} x{r['x0']}-{r['x1']} "
                             f"{r['verses']} [{r['reason']}]"))
        W = max(c.width for c, _ in cells) + 16
        H = sum(c.height + 30 for c, _ in cells) + 8
        sheet = Image.new("RGB", (W, H), (255, 255, 255))
        from PIL import ImageDraw
        dr = ImageDraw.Draw(sheet)
        y = 4
        for c, tag in cells:
            dr.text((8, y), tag[:120], fill=(0, 0, 0))
            sheet.paste(c, (8, y + 20))
            y += c.height + 30
        sheet.save(OUT / f"CL{cid}.png")
        print(f"CL{cid}.png n_members={len(members)}")


if __name__ == "__main__":
    main()
