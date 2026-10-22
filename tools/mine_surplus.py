"""Surplus-run mining loop (S14, S13 next-step 1).

Magenta runs NOT accounted for by known families:
  - no_cand: segments with n_mag_t==0 but mag runs present (every mag run
    belongs to an unlisted family) — unambiguous surplus;
  - amb_surplus: segments with n_mag_r > n_mag_t > 0 (suspects: crop all
    mag runs of the block).
Dedupe -> shape signatures (colored mask squashed to 16x48 + aspect) ->
greedy leader clustering -> atlas sheets per cluster under
/tmp/opencode/surplus_atlas (largest clusters first).

Outputs:
  tools/data/surplus_runs.json   manifest (run records + cluster ids)
  /tmp/opencode/surplus_atlas/cl{id}.png   member sheets
  /tmp/opencode/surplus_atlas/overview.png top-cluster representatives

Modes:
  default (no flag): surplus pool only (no_cand + amb_surplus segments).
  --all: EVERY mag run in mark_identity.json (S15 A1 ink-first tint
    dictionary: cluster all ~7.2k runs, read top clusters crop-by-crop).
    Manifest -> tools/data/mag_runs.json, atlas -> /tmp/opencode/mag_atlas.

Usage: python tools/mine_surplus.py [--all] [--top N] [--thresh T]
"""
import json
import sys
from pathlib import Path
from collections import Counter
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mark_identity import PICS, DATA
from rebuild_runs import page_bands

OUT = Path("/tmp/opencode/surplus_atlas")
CTX = 26          # context px each side for reading crops
GRID_W, GRID_H = 16, 48


@lru_cache(maxsize=64)
def get_page(p):
    from image_io import open_rgb
    return open_rgb(PICS / f"page_{p}.png")


@lru_cache(maxsize=4096)
def bands_of(p):
    try:
        return page_bands(p)
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return None


def crop_run(p, band, x0, x1, ctx=CTX):
    p, band, x0, x1 = int(p), int(band), int(x0), int(x1)
    bands = bands_of(p)
    y0, y1, _ = bands[band]
    im = get_page(p)
    a = np.asarray(im)[y0:y1 + 1, :, :]
    r = a[..., 0].astype(int)
    g = a[..., 1].astype(int)
    b = a[..., 2].astype(int)
    redish = (r - g > 45) & (r > 120)
    m = redish[:, x0:x1 + 1]
    ys, xs = np.where(m)
    if len(ys) == 0:
        return None, None
    bx0, bx1 = xs.min(), xs.max()
    by0, by1 = ys.min(), ys.max()
    mask = m[by0:by1 + 1, bx0:bx1 + 1]
    return mask, (int(bx0 + x0), int(by0 + y0), int(bx1 + x0), int(by1 + y0))


def signature(mask):
    h, w = mask.shape
    im = Image.fromarray((mask * 255).astype(np.uint8))
    im = im.resize((GRID_W, GRID_H), Image.BILINEAR)
    v = np.asarray(im, dtype=np.float32) / 255.0
    asp = np.log((w + 1.0) / (h + 1.0))
    return v.flatten(), asp


def reading_crop(p, band, x0, x1):
    bands = bands_of(p)
    y0, y1, _ = bands[band]
    im = get_page(p)
    W = im.width
    cx0 = max(0, x0 - CTX)
    cx1 = min(W, x1 + CTX)
    c = im.crop((cx0, y0, cx1, y1 + 1))
    z = 2
    return c.resize((c.width * z, c.height * z), Image.LANCZOS)


def collect_all():
    """All mag runs, any segment (A1 ink-first tint dictionary pool)."""
    d = json.load(open(DATA / "mark_identity.json"))
    seen = set()
    runs = []
    for seg in d["segments"]:
        for r in seg.get("runs", []):
            if r["kind"] != "mag" or r.get("page") is None:
                continue
            key = (r["page"], r["band"], r["x0"], r["x1"])
            if key in seen:
                continue
            seen.add(key)
            runs.append(dict(page=r["page"], band=r["band"], x0=r["x0"],
                             x1=r["x1"], npx=r["npx"], reason="all",
                             verses=seg.get("verses")))
    return runs


def collect():
    d = json.load(open(DATA / "mark_identity.json"))
    seen = set()
    runs = []
    for seg in d["segments"]:
        mt_, mr_ = seg.get("n_mag_t", 0), seg.get("n_mag_r", 0)
        if mr_ == 0:
            continue
        if mt_ == 0:
            reason = "no_cand"
        elif mr_ > mt_:
            reason = "amb_surplus"
        else:
            continue
        for r in seg.get("runs", []):
            if r["kind"] != "mag":
                continue
            key = (r.get("page"), r["band"], r["x0"], r["x1"])
            if key in seen or key[0] is None:
                continue
            seen.add(key)
            runs.append(dict(page=r["page"], band=r["band"], x0=r["x0"],
                             x1=r["x1"], npx=r["npx"], reason=reason,
                             verses=seg.get("verses"), seg_page=seg.get("page")))
    return runs


def main():
    thresh = 0.72
    top = 60
    args = sys.argv[1:]
    all_mode = "--all" in args
    if "--thresh" in args:
        thresh = float(args[args.index("--thresh") + 1])
    if "--top" in args:
        top = int(args[args.index("--top") + 1])
    if all_mode:
        out = Path("/tmp/opencode/mag_atlas")
        manifest = DATA / "mag_runs.json"
        runs = collect_all()
    else:
        out = OUT
        manifest = DATA / "surplus_runs.json"
        runs = collect()
    print(f"mag runs ({'ALL' if all_mode else 'surplus'}): {len(runs)}")
    feats, asps = [], []
    keep = []
    for r in runs:
        mask, _ = crop_run(r["page"], r["band"], r["x0"], r["x1"])
        if mask is None:
            continue
        f, a = signature(mask)
        feats.append(f)
        asps.append(a)
        keep.append(r)
    F = np.stack(feats)
    A = np.array(asps, dtype=np.float32)
    Fn = F / (np.linalg.norm(F, axis=1, keepdims=True) + 1e-9)
    print(f"signatures: {Fn.shape}")
    # greedy leader clustering (preallocated leader matrix)
    n = len(Fn)
    lab = -np.ones(n, dtype=int)
    L = np.zeros((n, Fn.shape[1]), dtype=np.float32)
    LA = np.zeros(n, dtype=np.float32)
    k = 0
    for i in range(n):
        if k:
            sims = Fn[i] @ L[:k].T - 0.4 * np.abs(A[i] - LA[:k])
            j = int(np.argmax(sims))
            if sims[j] >= thresh:
                lab[i] = j
                continue
        lab[i] = k
        L[k] = Fn[i]
        LA[k] = A[i]
        k += 1
    print(f"clusters: {k} at thresh={thresh}")
    sizes = Counter(lab.tolist())
    print("top sizes:", sizes.most_common(15))
    # manifest
    for i, r in enumerate(keep):
        r["cluster"] = int(lab[i])
        r["id"] = i
    manifest.write_text(json.dumps(keep))
    out.mkdir(parents=True, exist_ok=True)
    # per-cluster sheets (largest first)
    by_cl = {}
    for i, r in enumerate(keep):
        by_cl.setdefault(lab[i], []).append(i)
    big = [c for c, _ in sizes.most_common() if sizes[c] >= 2]
    for cid in big[:top]:
        members = by_cl[cid][:10]
        cells = []
        for i in members:
            r = keep[i]
            c = reading_crop(r["page"], r["band"], r["x0"], r["x1"])
            tag = (f"p{r['page']} b{r['band']} x{r['x0']} {r['verses']} "
                   f"[{r['reason']}]")
            cells.append((c, tag))
        cw, ch = 480, 190
        cols = 2
        rows = (len(cells) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cw, rows * ch), (250, 250, 250))
        dr = ImageDraw.Draw(sheet)
        for kk, (c, tag) in enumerate(cells):
            gx, gy = (kk % cols) * cw, (kk // cols) * ch
            sc = min((cw - 10) / c.width, (ch - 26) / c.height, 3.0)
            if sc < 1:
                c = c.resize((max(1, int(c.width * sc)),
                              max(1, int(c.height * sc))))
            dr.text((gx + 4, gy + 4), tag[:64], fill=(0, 0, 0))
            sheet.paste(c, (gx + 4, gy + 22))
        sheet.save(out / f"cl{cid:03d}.png")
    # overview: one representative per cluster, size order
    ov = []
    for cid, _ in sizes.most_common(top):
        i = by_cl[cid][0]
        r = keep[i]
        c = reading_crop(r["page"], r["band"], r["x0"], r["x1"])
        ov.append((c, f"cl{cid} n={sizes[cid]} p{r['page']} b{r['band']} "
                      f"{r['verses']}"))
    cw, ch = 480, 190
    cols = 2
    rows = (len(ov) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, rows * ch), (255, 255, 255))
    dr = ImageDraw.Draw(sheet)
    for kk, (c, tag) in enumerate(ov):
        gx, gy = (kk % cols) * cw, (kk // cols) * ch
        sc = min((cw - 10) / c.width, (ch - 26) / c.height, 3.0)
        if sc < 1:
            c = c.resize((max(1, int(c.width * sc)), max(1, int(c.height * sc))))
        dr.text((gx + 4, gy + 4), tag[:64], fill=(0, 0, 0))
        sheet.paste(c, (gx + 4, gy + 22))
    sheet.save(out / "overview.png")
    print(f"atlas: {min(top, len(big))} cluster sheets + overview -> {out}")


if __name__ == "__main__":
    main()
