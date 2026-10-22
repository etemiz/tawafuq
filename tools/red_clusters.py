import json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from image_io import open_rgb

sys.path.insert(0, str(Path(__file__).resolve().parent))
PICS = Path(__file__).resolve().parent.parent / "hayrat-pics"
DATA = Path(__file__).resolve().parent / "data" / "real_boxes"
OUT = Path(__file__).resolve().parent / "data" / "red_feats.npz"

def crops():
    feats, meta = [], []
    for f in sorted(DATA.glob("page_*.json")):
        d = json.loads(f.read_text())
        n = d["page"]
        im = open_rgb(PICS / f"page_{n}.png").convert("L")
        for i, r in enumerate(d["reds"]):
            if r["line"] is None:
                continue
            x0, x1, y0, y1 = r["x0"], r["x1"], r["y0"], r["y1"]
            crop = im.crop((x0, y0, x1 + 1, y1 + 1))
            a = 255 - np.asarray(crop, dtype=np.float64)
            if a.sum() < 50:
                continue
            yy, xx = np.where(a > 40)
            if len(yy) < 20:
                continue
            sub = a[yy.min():yy.max() + 1, xx.min():xx.max() + 1]
            ih, iw = sub.shape
            scale = 48.0 / max(ih, iw)
            nh, nw = max(1, int(round(ih * scale))), max(1, int(round(iw * scale)))
            small = np.asarray(Image.fromarray(sub).resize((nw, nh)),
                               dtype=np.float64)
            canvas = np.zeros((56, 56))
            oy, ox = (56 - nh) // 2, (56 - nw) // 2
            canvas[oy:oy + nh, ox:ox + nw] = small
            if canvas.sum() > 0:
                canvas /= canvas.sum()
            feats.append(canvas.ravel())
            meta.append((n, i, r["cx"], r["line"], r["w"], r["h"]))
    return np.array(feats), meta

def kmeans(X, k, iters=25, seed=5):
    rng = np.random.default_rng(seed)
    C = X[rng.choice(len(X), k, replace=False)]
    norms = (X * X).sum(axis=1)
    def distances():
        # Avoid the N x K x feature-dimension tensor (~1.6GB for this pool).
        return np.maximum(0.0, norms[:, None] + (C * C).sum(axis=1)[None, :] - 2 * (X @ C.T))
    for _ in range(iters):
        D = distances()
        lab = D.argmin(axis=1)
        for c in range(k):
            pts = X[lab == c]
            if len(pts):
                C[c] = pts.mean(axis=0)
    D = distances()
    return D.argmin(axis=1), C

def main():
    X, meta = crops()
    print("feats:", X.shape)
    k = 14
    lab, C = kmeans(X, k)
    sizes = np.bincount(lab, minlength=k)
    order = np.argsort(-sizes)
    for c in order:
        idxs = np.where(lab == c)[0]
        ex = [meta[i] for i in idxs[:3]]
        print(f"cluster {c}: n={sizes[c]:4d} ex={ex}")
    np.savez_compressed(OUT, X=X, lab=lab, C=C,
             meta=np.array(meta, dtype=np.float64))

if __name__ == "__main__":
    main()
