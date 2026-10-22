import sys, json
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_scan import load_page, black_mask, text_region, components, dilate, text_lines

SPECK_W, SPECK_H = 30, 14
BIG_H, BIG_W_FRAC = 120, 0.30
XGAP, YGAP = 14, 26

def extract_page(n):
    a = load_page(n)
    bm = black_mask(a)
    H, W = bm.shape
    ty0, ty1, bx0, bx1 = text_region(bm)
    ink = np.zeros_like(bm)
    ink[ty0:ty1 + 1, bx0:bx1] = bm[ty0:ty1 + 1, bx0:bx1]
    comps = components(a, ink, dilate(ink, 5), 30)
    words = []
    for c in comps:
        w = c["x1"] - c["x0"] + 1
        h = c["y1"] - c["y0"] + 1
        if w < SPECK_W and h < SPECK_H:
            continue
        if h > BIG_H or w > BIG_W_FRAC * W:
            continue
        words.append(c)
    out = [dict(c) for c in words]
    changed = True
    while changed:
        changed = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                p, q = out[i], out[j]
                if p is None or q is None:
                    continue
                gx = max(p["x0"] - q["x1"], q["x0"] - p["x1"])
                oy = min(p["y1"], q["y1"]) - max(p["y0"], q["y0"])
                gy = max(p["y0"] - q["y1"], q["y0"] - p["y1"])
                if gx <= XGAP and (oy > 0 or gy <= YGAP):
                    p["x0"] = min(p["x0"], q["x0"]); p["x1"] = max(p["x1"], q["x1"])
                    p["y0"] = min(p["y0"], q["y0"]); p["y1"] = max(p["y1"], q["y1"])
                    p["npx"] += q["npx"]
                    p["cy"] = (p["y0"] + p["y1"]) / 2.0
                    p["cx"] = (p["x0"] + p["x1"]) / 2.0
                    out[j] = None
                    changed = True
        out = [c for c in out if c is not None]
    for c in out:
        c["w"] = c["x1"] - c["x0"] + 1
        c["h"] = c["y1"] - c["y0"] + 1
    bands = text_lines(bm, ty0, ty1, bx0, bx1)
    pitch = np.median([b[1] - b[0] for b in bands]) if bands else 60
    lines = []
    for c in out:
        best, bd = None, 1e9
        for bi, (b0, b1) in enumerate(bands):
            d = abs(c["cy"] - (b0 + b1) / 2.0)
            if d < bd:
                best, bd = bi, d
        c["line"] = best if bd <= pitch * 0.9 else -1
    return dict(page=n, ty=[int(ty0), int(ty1)], bx=[int(bx0), int(bx1)],
                bands=[(int(b0), int(b1)) for b0, b1 in bands],
                words=[dict(x0=c["x0"], x1=c["x1"], y0=c["y0"], y1=c["y1"],
                            cx=round(c["cx"], 1), cy=round(c["cy"], 1),
                            w=c["w"], h=c["h"], line=c["line"]) for c in out])

def main():
    first, last = int(sys.argv[1]), int(sys.argv[2])
    outdir = Path(__file__).resolve().parent / "data" / "boxes"
    outdir.mkdir(parents=True, exist_ok=True)
    for n in range(first, last + 1):
        f = outdir / f"page_{n:03d}.json"
        if f.exists():
            continue
        try:
            d = extract_page(n)
        except Exception as e:
            print(f"page {n}: ERROR {e}", flush=True)
            continue
        f.write_text(json.dumps(d))
        print(f"page {n}: {len(d['words'])} words, {len(d['bands'])} bands", flush=True)

if __name__ == "__main__":
    main()
