import json
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

PICS = Path(__file__).resolve().parent.parent / "hayrat-pics"
OUT = Path(__file__).resolve().parent / "data" / "rosettes.json"

def gold_mask(im):
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    return (R > 90) & (R - B > 70) & (G - B > 70) & (B < 90) & (np.abs(R - G) < 45)

def rosettes(im):
    m = gold_mask(im)
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    if n == 0:
        return []
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    objs = ndimage.find_objects(lab)
    cand = []
    for s, o in zip(sizes, objs):
        if s < 380:
            continue
        h = o[0].stop - o[0].start
        w = o[1].stop - o[1].start
        if not (26 <= h <= 52):
            continue
        if not (26 <= w <= 64):
            continue
        if s < 0.22 * w * h:
            continue
        cy = (o[0].start + o[0].stop) / 2.0
        cx = (o[1].start + o[1].stop) / 2.0
        if not (120 <= cy <= 1680):
            continue
        cand.append(dict(cx=round(cx, 1), cy=round(cy, 1), npx=int(s), n=1))
    # merged touching rosettes: wide flat blobs
    for s, o in zip(sizes, objs):
        if s < 700:
            continue
        h = o[0].stop - o[0].start
        w = o[1].stop - o[1].start
        if not (26 <= h <= 52 and 65 <= w <= 170 and s >= 0.18 * w * h):
            continue
        cy = (o[0].start + o[0].stop) / 2.0
        cx = (o[1].start + o[1].stop) / 2.0
        if not (120 <= cy <= 1680):
            continue
        cand.append(dict(cx=round(cx, 1), cy=round(cy, 1), npx=int(s),
                         n=max(2, round(w / 40.0))))
    cand.sort(key=lambda r: (r["cy"], -r["cx"]))
    return cand

def main():
    res = {}
    for p in range(1, 605):
        f = PICS / f"page_{p}.png"
        if not f.exists():
            continue
        im = np.asarray(Image.open(f).convert("RGB")).astype(int)
        res[str(p)] = rosettes(im)
    OUT.write_text(json.dumps(res))
    tot = sum(sum(r.get("n", 1) for r in v) for v in res.values())
    print("pages:", len(res), "total rosettes:", tot)
    from collections import Counter
    cnt = Counter(sum(r.get("n", 1) for r in v) for v in res.values())
    print("count histogram:", dict(sorted(cnt.items())))

if __name__ == "__main__":
    main()
