"""Cluster sign blobs by shape and build per-cluster contact sheets.

Renders each sign as a normalized 48x48 binary thumbnail, k-means clusters
per (ink, w-class), saves sheets + cluster assignment npz/json.
"""
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
PICS = ROOT.parent / "hayrat-pics"
OUT = Path("/tmp/opencode/sign_clusters")
NC = 12


def thumb(im, s, size=48):
    pad = 4
    c = im.crop((max(0, s["x0"] - pad), max(0, s["y0"] - pad),
                 s["x1"] + pad, s["y1"] + pad)).convert("RGB")
    a = np.asarray(c).astype(np.int16)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    redish = ((R - G > 45) & (R > 120)).astype(np.uint8) * 255
    t = Image.fromarray(redish)
    # pad to square-ish aspect
    w, h = t.size
    tw = max(w, int(h * 1.6))
    canvas = Image.new("L", (tw + 8, h + 8), 0)
    canvas.paste(t, ((tw - w) // 2 + 4, 4))
    canvas = canvas.resize((size, size), Image.NEAREST)
    v = np.asarray(canvas).astype(np.float32) / 255.0
    return v.flatten()


def main():
    S = json.load(open(ROOT / "data" / "sign_catalog.json"))
    OUT.mkdir(parents=True, exist_ok=True)
    groups = defaultdict(list)
    for i, s in enumerate(S):
        if s["w"] > 60:
            continue
        key = (s["ink"], "w<=32" if s["w"] <= 32 else "w33-60")
        groups[key].append(i)
    rng = np.random.default_rng(11)
    all_lab = {}
    for key, idxs in sorted(groups.items()):
        if len(idxs) < 40:
            continue
        if len(idxs) > 3000:
            idxs = list(rng.permutation(idxs)[:3000])
        X = []
        ims = {}
        for i in idxs:
            s = S[i]
            if s["pg"] not in ims:
                ims[s["pg"]] = Image.open(PICS / f"page_{s['pg']}.png").convert("RGB")
            X.append(thumb(ims[s["pg"]], s))
        X = np.array(X)
        # kmeans
        from scipy.cluster.vq import kmeans2
        cent, lab = kmeans2(X, NC, minit="++", seed=7, iter=30)
        # order clusters by size
        order = np.argsort(-np.bincount(lab, minlength=NC))
        remap = {old: new for new, old in enumerate(order)}
        lab2 = np.array([remap[int(l)] for l in lab])
        for j, i in enumerate(idxs):
            all_lab[str(i)] = int(lab2[j])
        # sheet: 8 nearest to center + 8 random per cluster
        for c in range(NC):
            idx_c = [j for j in range(len(idxs)) if lab2[j] == c]
            if len(idx_c) < 5:
                continue
            D = ((X[idx_c] - cent[c]) ** 2).sum(axis=1)
            near = [idx_c[k] for k in np.argsort(D)[:4]]
            rest = [j for j in idx_c if j not in near]
            rnd = list(rng.choice(rest, size=min(4, len(rest)), replace=False)) if rest else []
            sel = near + rnd
            cells = []
            for j in sel:
                i = idxs[j]
                s = S[i]
                if s["pg"] not in ims:
                    ims[s["pg"]] = Image.open(PICS / f"page_{s['pg']}.png").convert("RGB")
                im = ims[s["pg"]]
                pad = 4
                cimg = im.crop((max(0, s["x0"] - pad), max(0, s["y0"] - pad),
                                s["x1"] + pad, s["y1"] + pad))
                z = max(1, int(120 / max(cimg.width, cimg.height)))
                cimg = cimg.resize((cimg.width * z, cimg.height * z), Image.LANCZOS)
                cells.append((cimg, f"p{s['pg']}"))
            cw, ch = 180, 210
            sheet = Image.new("RGB", (8 * cw, 2 * ch), (250, 250, 250))
            dr = ImageDraw.Draw(sheet)
            for k, (cimg, tag) in enumerate(cells[:16]):
                gx, gy = (k % 8) * cw, (k // 8) * ch
                if cimg.width > cw - 6 or cimg.height > ch - 22:
                    sc = min((cw - 6) / cimg.width, (ch - 22) / cimg.height)
                    cimg = cimg.resize((max(1, int(cimg.width * sc)), max(1, int(cimg.height * sc))))
                dr.text((gx + 3, gy + 3), tag, fill=(0, 0, 0))
                sheet.paste(cimg, (gx + 3, gy + 20))
            sheet.save(OUT / f"{key[0]}_{key[1]}_c{c}.png")
        print(key, len(idxs), "->", NC, "clusters; sizes", np.bincount(lab2, minlength=NC).tolist())
    json.dump(all_lab, open(OUT / "cluster_map.json", "w"))
    print("sheets in", OUT)


if __name__ == "__main__":
    main()