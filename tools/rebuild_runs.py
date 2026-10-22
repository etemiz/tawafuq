"""Run-based token map rebuild (token_map3).

token_map2's DP works on over-fragmented slots: skip penalties are cheap
relative to width costs, so tokens shift by whole words at band boundaries
(pitfall 12; crimson-anchor audit: ~48% of divine-name records misaligned).

This rebuild replaces the slot stream with PIXEL INK RUNS per band: for each
band (existing line grid + keep_strips strip handling), the page image's ink
columns are segmented into word-ish runs (over-segmented: intra-word gaps
also split), and page_dp maps tokens onto runs with merging allowed (G up to
6). Runs are word-sized, so the DP has far fewer degenerate optima.

Spans are REUSED from token_map2.json (rosette ground truth, untouched).
Output: token_map3.json. Acceptance test = tools/audit_crimson.py.
"""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from image_io import open_rgb

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_tokens as mt
from patch_strip_map import page_offsets

DATA = Path(__file__).resolve().parent / "data"
PICS = Path(__file__).resolve().parent.parent / "hayrat-pics"

INK = 600          # rgb-sum threshold for ink (kashida-safe: 680 welds words)
GAP = 10           # column gap -> separate runs (word-ish)
MINGAP = 0         # unused
LAMB_RUNS = 2.0    # skip penalty per RUN (a run ~= a word; skipping is costly)
GMAX = 6           # max runs merged into one token


def page_bands(n, boxes=DATA / "real_boxes"):
    """Bands from real_boxes slots: same band structure as keep_strips
    (line ids, None-line slots clustered + flagged strip=1, disjoint-band
    line splits). Returns list of (y0, y1, strip) — pixel y bounds."""
    f = boxes / f"page_{n:03d}.json"
    d = json.loads(f.read_text())
    if d["grid"] is None:
        return None
    slots = [s for s in d["slots"] if s["color"] != "gold"]
    lines = {}
    strips = []
    for s in slots:
        if s["line"] is None:
            strips.append(s)
            continue
        lines.setdefault(s["line"], []).append(s)
    units = []
    if strips:
        strips.sort(key=lambda c: (c["y0"] + c["y1"]) / 2)
        bands = []
        for c in strips:
            cy = (c["y0"] + c["y1"]) / 2
            if bands and cy - bands[-1][0] < 60:
                bands[-1][0] = cy
                bands[-1][1].append(c)
            else:
                bands.append([cy, [c]])
        for cy, grp in bands:
            units.append(((min(c["y0"] for c in grp), max(c["y1"] for c in grp)),
                          True))
    for li, ss in lines.items():
        units.append(((min(c["y0"] for c in ss), max(c["y1"] for c in ss)),
                      False))
    units.sort(key=lambda u: u[0][0])
    # split bands whose slots form disjoint y-groups (>55px cy gaps)
    raw = []
    for (y0, y1), strip in units:
        ss = [s for s in slots
              if y0 <= (s["y0"] + s["y1"]) / 2 <= y1]
        ss = sorted(ss, key=lambda c: (c["y0"] + c["y1"]) / 2)
        bands2 = []
        for c in ss:
            cy = (c["y0"] + c["y1"]) / 2
            if bands2 and cy - bands2[-1][0] < 55:
                bands2[-1][0] = cy
                bands2[-1][1].append(c)
            else:
                bands2.append([cy, [c]])
        for cy, grp in bands2:
            raw.append((int(min(c["y0"] for c in grp)),
                        int(max(c["y1"] for c in grp)), strip))
    # pad bands toward their ink (clipped ascenders/descenders) but never
    # overlap a neighbour: pad = min(14, gap/2 - 3)
    out = []
    for i, (y0, y1, strip) in enumerate(raw):
        lo_gap = y0 - raw[i - 1][1] if i > 0 else 999
        hi_gap = raw[i + 1][0] - y1 if i < len(raw) - 1 else 999
        pad_lo = max(0, min(14, lo_gap // 2 - 3))
        pad_hi = max(0, min(14, hi_gap // 2 - 3))
        out.append((y0 - pad_lo, y1 + pad_hi, strip))
    return out


def rosette_mask(n, y0, y1, shape_w):
    """Exclude rosette disks (dark digits read as ink) — only for bands whose
    y-range overlaps the rosette's disk. Returns column keep-mask."""
    keep = np.ones(shape_w, dtype=bool)
    try:
        d = np.load(DATA / "rosette_seq.npz")
        mm = d["meta"]
    except Exception:
        return keep
    for row in mm:
        pg, cx, cy = int(row[0]), row[1], row[2]
        if pg != n or cx < 0:
            continue
        if not (y0 - 45 < cy < y1 + 45):
            continue
        lo = max(0, int(cx - 38))
        hi = min(shape_w, int(cx + 39))
        keep[lo:hi] = False
    return keep


def band_runs(n, y0, y1):
    """Pixel ink runs of the band as boxes (dicts like stream slots)."""
    f = PICS / f"page_{n}.png"
    if not f.exists():
        return []
    im = np.asarray(open_rgb(f))[y0:y1, :, :]
    r, g, b = im[..., 0].astype(int), im[..., 1].astype(int), im[..., 2].astype(int)
    ink = (r + g + b < INK) | ((r - g > 45) & (r > 120))
    ink[:, ~rosette_mask(n, y0, y1, im.shape[1])] = False
    col = ink.sum(axis=0)
    runs = []
    x = 0
    W = len(col)
    while x < W:
        if col[x] >= 2:
            x0 = x
            gap = 0
            while x < W:
                if col[x] >= 1:
                    gap = 0
                else:
                    gap += 1
                    if gap > GAP:
                        break
                x += 1
            x1 = x - gap
            if x1 - x0 >= 8:
                runs.append((x0, x1))
        else:
            x += 1
    # merge runs separated by < 4px (anti-alias splits), then order RTL
    mg = []
    for x0, x1 in runs:
        if mg and x0 - mg[-1][1] <= 3:
            mg[-1][1] = x1
        else:
            mg.append([x0, x1])
    mg.reverse()
    out = []
    for x0, x1 in mg:
        sub = ink[:, x0:x1 + 1]
        npx = int(sub.sum())
        out.append(dict(x0=int(x0), x1=int(x1), y0=y0, y1=y1,
                        cx=(x0 + x1) / 2.0, cy=(y0 + y1) / 2.0,
                        npx=npx, line=0, color="ink", strip=0))
    return out


def color_col_runs(n, y0, y1, kind):
    """Colored ink column runs in a band slice. Same thresholds as
    phrase_census.color_runs (gap break 22, min_len 12). kind: crimson|mag.
    Returns [(x0, x1)] in x-ASC order."""
    f = PICS / f"page_{n}.png"
    if not f.exists():
        return []
    im = np.asarray(open_rgb(f))[y0:y1, :, :]
    r, g, b = im[..., 0].astype(int), im[..., 1].astype(int), im[..., 2].astype(int)
    redish = (r - g > 45) & (r > 120)
    mask = redish & ((b >= 108) if kind == "mag" else (b < 108))
    col = mask.sum(axis=0)
    runs = []
    x = 0
    W = len(col)
    while x < W:
        if col[x] >= 3:
            x0 = x
            gap = 0
            while x < W:
                if col[x] >= 2:
                    gap = 0
                else:
                    gap += 1
                    if gap > 22:
                        break
                x += 1
            x1 = x - gap
            if x1 - x0 >= 12:
                runs.append((x0, x1))
        else:
            x += 1
    return runs


def page_dp_runs(stream, toks, lamb=LAMB_RUNS, gmax=GMAX):
    n, m = len(stream), len(toks)
    if n == 0 or m == 0:
        return None, None
    x1 = np.array([b["x1"] for b in stream], dtype=np.float64)
    x0 = np.array([b["x0"] for b in stream], dtype=np.float64)
    wseg = x1 - x0 + 1
    cumw = np.concatenate([[0.0], np.cumsum(wseg)])
    est = np.array([mt.est_width(t) for t in toks])
    INF = 1e12
    LAMT = 3.0
    D = np.full((m + 1, n + 1), INF)
    PI = np.full((m + 1, n + 1), -2, dtype=np.int16)
    PJ = np.full((m + 1, n + 1), -2, dtype=np.int16)
    D[0, 0] = 0.0
    for i in range(m + 1):
        fin = np.where(D[i] < INF / 2)[0]
        if len(fin) == 0:
            continue
        base = np.full(n + 1, INF)
        base[fin] = D[i][fin] - lamb * fin
        cummin = np.minimum.accumulate(base)
        rec = np.where(base == cummin)[0]
        if len(rec):
            j0s = rec[np.searchsorted(rec, np.arange(n + 1), side="right") - 1]
            j0s = np.clip(j0s, 0, n)
            Dsh = np.where(cummin < INF / 2,
                           cummin + lamb * np.arange(n + 1), INF)
            upd = (Dsh < D[i] - 1e-9) & (j0s < np.arange(n + 1))
            D[i] = np.where(upd, Dsh, D[i])
            PI[i] = np.where(upd, i, PI[i])
            PJ[i] = np.where(upd, j0s, PJ[i])
        if i == m:
            continue
        src = D[i]
        tgt = D[i + 1]
        upd = src + LAMT < tgt
        D[i + 1] = np.where(upd, src + LAMT, tgt)
        PI[i + 1] = np.where(upd, i, PI[i + 1])
        PJ[i + 1] = np.where(upd, np.arange(n + 1), PJ[i + 1])
        for g in range(1, gmax + 1):
            if g > n:
                break
            srcj = np.arange(0, n + 1 - g)
            base2 = D[i][srcj]
            got = cumw[srcj + g] - cumw[srcj]
            span = x1[srcj] - x0[srcj + g - 1] + 1
            width = np.maximum(span, got * 0.65) + 6.0 * (g - 1)
            wc = np.abs(width - est[i]) / max(est[i], 24.0)
            cand = base2 + wc * 4.0 + 0.08 * (g - 1)
            cand = np.where(base2 < INF / 2, cand, INF)
            tgt2 = D[i + 1, g:n + 1]
            upd2 = cand < tgt2
            D[i + 1, g:n + 1] = np.where(upd2, cand, tgt2)
            PI[i + 1, g:n + 1] = np.where(upd2, i, PI[i + 1, g:n + 1])
            PJ[i + 1, g:n + 1] = np.where(upd2, srcj, PJ[i + 1, g:n + 1])
    if D[m, n] >= INF / 2:
        return None, None
    i, j = m, n
    mapping = [None] * m
    steps = 0
    while (i > 0 or j > 0) and steps < 4 * (m + n) + 10:
        steps += 1
        pi, pj = int(PI[i, j]), int(PJ[i, j])
        if pi < 0 or pj < 0:
            return None, None
        if pi == i:
            j = pj
        elif pj == j:
            i = pi
            mapping[i] = []
        else:
            mapping[pi] = list(range(pj, j))
            i, j = pi, pj
    if steps >= 4 * (m + n) + 10:
        return None, None
    return float(D[m, n]), mapping


def main():
    verses = mt.load_tokens()
    tm = json.loads((DATA / "token_map2.json").read_text())
    spans = [tuple(tm["spans"][str(p + 1)]) if str(p + 1) in tm["spans"]
             else None for p in range(604)]
    off = page_offsets(spans, verses)
    out = []
    tok_idx = off[1][0] if 1 in off else next(iter(off.values()))[0]
    nfail = 0
    nskip = 0
    wres = []
    for p in range(604):
        sp = spans[p]
        if sp is None:
            continue
        page = p + 1
        s0, s1 = sp
        toks = [t for i in range(s0, s1 + 1) for t in verses[i][2]]
        bands = page_bands(page)
        if bands is None:
            for _ in range(len(toks)):
                out.append(dict(t=tok_idx, page=page, boxes=[], skip=True))
                tok_idx += 1
            continue
        stream = []
        for bi, (y0, y1, strip) in enumerate(bands):
            rr = band_runs(page, y0, y1)
            for b in rr:
                b["line"] = bi
                b["strip"] = int(strip)
            stream.extend(rr)
        cost, mapping = page_dp_runs(stream, toks)
        if mapping is None:
            nfail += 1
            print(f"p{page}: RUN DP FAILED ({len(stream)} runs vs {len(toks)} toks)")
            for _ in range(len(toks)):
                out.append(dict(t=tok_idx, page=page, boxes=[], skip=True))
                tok_idx += 1
            continue
        for gi, g in enumerate(mapping):
            t = tok_idx
            tok_idx += 1
            if g is None or len(g) == 0:
                out.append(dict(t=t, page=page, boxes=[], skip=True))
                nskip += 1
                continue
            bs = [stream[j] for j in g]
            rec = dict(t=t, page=page,
                       boxes=[b["cx"] for b in bs],
                       x=[min(b["x0"] for b in bs), max(b["x1"] for b in bs)],
                       y=[int(min(b["y0"] for b in bs)),
                          int(max(b["y1"] for b in bs))],
                       line=bs[0]["line"],
                       n=len(bs),
                       npx=sum(b["npx"] for b in bs),
                       span=bs[0]["x1"] - bs[-1]["x0"] + 1)
            if any(b.get("strip") for b in bs):
                rec["strip"] = 1
            out.append(rec)
            wres.append(abs((bs[0]["x1"] - bs[-1]["x0"] + 1)
                            - mt.est_width(toks[gi]))
                        / max(mt.est_width(toks[gi]), 24.0))
    print(f"pages failed: {nfail}, token skips: {nskip}, "
          f"mean width residual: {np.mean(wres):.3f}" if wres else "")
    Path(DATA / "token_map3.json").write_text(json.dumps(
        dict(spans=tm["spans"], map=out)))
    print("saved token_map3.json;", len(out), "records")


if __name__ == "__main__":
    main()
