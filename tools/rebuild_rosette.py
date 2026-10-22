"""Rosette-anchored token map rebuild (token_map3).

token_map2's slot-DP is corrupted corpus-wide (pitfall 12): kashida
justification makes token widths unpredictable and skip penalties are cheap,
so tokens drift by whole words/lines; the crimson-anchor audit flagged ~48%
of divine-name records.

This rebuild anchors on ROSETTES (verse-end rosettes = ground truth, digit-
read): between consecutive rosettes the token list is exactly known, so each
verse's tokens are assigned only to the ink runs between the previous and
this rosette. Ink runs come from pixel segmentation per band (word-ish
units, rosette disks masked). n_runs == n_tokens segments are forced 1:1.

Spans are REUSED from token_map2.json. Output: token_map3.json.
Acceptance: tools/audit_crimson.py + p154 pixel truth.
"""
import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import map_tokens as mt
from rebuild_runs import (page_bands, band_runs, page_dp_runs,
                          color_col_runs)

DATA = Path(__file__).resolve().parent / "data"
PINS_ONLY = "--pins-only" in sys.argv


def load_rosettes():
    d = np.load(DATA / "rosette_seq.npz")["meta"]
    by_page = {}
    for row in d:
        pg, cx, cy, s, v = int(row[0]), row[1], row[2], int(row[3]), int(row[4])
        if cx < 0 or s <= 0:
            continue
        by_page.setdefault(pg, []).append((cy, -cx, cx, s, v))
    for pg in by_page:
        by_page[pg].sort()  # reading order: y asc, x desc
    return by_page


NAMES = {"الله", "لله", "رب", "ربنا", "ربكم", "ربك", "ربهم", "ربه", "ربي"}
MAG_WORDS = ({"لا", "اله", "الا", "هو", "اذا", "انزلت", "سوره", "العرش",
              "العظيم", "الجنه", "بما", "كنتم", "عليكم", "اورثتموها",
              "اصحب", "النار", "ايمنا", "انزلت"})


def pin_dp(block, runs, cand_i, cand_j):
    """Monotonic DP between candidate tokens (block indices) and candidate
    runs (run indices, RTL order). Transitions: skip token / skip run /
    1:1 pin (width cost). Returns [(i, j)] trusted pins."""
    ti = list(cand_i)
    rj = list(cand_j)
    m, n = len(ti), len(rj)
    if m == 0 or n == 0:
        return []
    est = [max(mt.est_width(block[k]), 24.0) for k in ti]
    w = [runs[j]["x1"] - runs[j]["x0"] + 1 for j in rj]
    SKIP_T, SKIP_R = 3.0, 3.0
    INF = 1e9
    D = np.full((m + 1, n + 1), INF)
    BK = np.full((m + 1, n + 1), -2, np.int8)
    D[0, 0] = 0.0
    for j in range(1, n + 1):
        D[0, j] = D[0, j - 1] + SKIP_R
    for i in range(1, m + 1):
        D[i, 0] = D[i - 1, 0] + SKIP_T
        for j in range(1, n + 1):
            best, bk = D[i - 1, j] + SKIP_T, 0      # token skipped
            c = D[i, j - 1] + SKIP_R                 # run skipped
            if c < best:
                best, bk = c, 1
            c = D[i - 1, j - 1] + abs(w[j - 1] - est[i - 1]) / est[i - 1]
            if c < best:
                best, bk = c, 2                      # 1:1 pin
            D[i, j] = best
            BK[i, j] = bk
    pins = []
    i, j = m, n
    while i > 0 and j > 0:
        bk = BK[i, j]
        if bk == 2:
            pins.append((ti[i - 1], rj[j - 1]))
            i -= 1
            j -= 1
        elif bk == 1:
            j -= 1
        else:
            i -= 1
    return [(i, j) for i, j in reversed(pins)
            if abs(runs[j]["x1"] - runs[j]["x0"] + 1
                   - max(mt.est_width(block[i]), 24.0))
            / max(mt.est_width(block[i]), 24.0) < 0.35]


def assign_segment(runs, block):
    """Assign tokens of one rosette segment to runs.
    Returns (list of run-index-lists per token, n_skipped_tokens)."""
    n, m = len(runs), len(block)
    res = [None] * m
    if n == 0:
        return None, m
    if n == m:
        return [[k] for k in range(n)], 0
    page = runs[0]["page"] if "page" in runs[0] else None
    pins = []
    if page is not None:
        # per-band colored runs (never mix bands in one column profile)
        by_band = {}
        for j, b in enumerate(runs):
            by_band.setdefault(b["line"], []).append(j)
        cri_cand, mag_cand = [], []
        for bd, jlist in by_band.items():
            y0 = min(runs[j]["y0"] for j in jlist)
            y1 = max(runs[j]["y1"] for j in jlist)
            cri = color_col_runs(page, y0, y1, "crimson")
            mag = color_col_runs(page, y0, y1, "mag")
            for j in jlist:
                cx = runs[j]["cx"]
                if any(c0 < cx < c1 for c0, c1 in cri):
                    cri_cand.append(j)
                if any(c0 < cx < c1 for c0, c1 in mag):
                    mag_cand.append(j)
        if cri_cand:
            div_i = [k for k, t in enumerate(block) if t in NAMES]
            pins += pin_dp(block, runs, div_i, cri_cand)
        if mag_cand:
            fam_i = [k for k, t in enumerate(block) if t in MAG_WORDS]
            used_t = {i for i, _ in pins}
            used_r = {j for _, j in pins}
            fam_i = [i for i in fam_i if i not in used_t]
            mag_cand = [j for j in mag_cand if j not in used_r]
            pins += pin_dp(block, runs, fam_i, mag_cand)
        if PINS_ONLY:
            # anchored-only map: keep precisely-pinned tokens, skip the rest
            res = [None] * m
            for i, j in pins:
                res[i] = [j]
            return res, m - len(pins)
    if not pins:
        _c, mapping = page_dp_runs(runs, block, lamb=1.5)
        if mapping is None:
            return None, m
        return [list(g) if g else None for g in mapping], sum(
            1 for g in mapping if not g)
    # distribute between pins
    pins.sort()
    bounds = [(-1, -1)] + pins + [(m, n)]
    nskip = 0
    for (i1, j1), (i2, j2) in zip(bounds, bounds[1:]):
        toks_rng = list(range(i1 + 1, i2))
        runs_rng = list(range(j1 + 1, j2))
        if not toks_rng:
            continue
        sub = [runs[j] for j in runs_rng]
        sub_blocks = [block[k] for k in toks_rng]
        if len(runs_rng) == len(toks_rng):
            for k, t_i in enumerate(toks_rng):
                res[t_i] = [runs_rng[k]]
        else:
            _c, mapping = page_dp_runs(sub, sub_blocks, lamb=1.5)
            if mapping is None:
                nskip += len(toks_rng)
                continue
            for gi, g in enumerate(mapping):
                res[toks_rng[gi]] = [runs_rng[j] for j in g] if g else None
                if not g:
                    nskip += 1
    return res, nskip


def build_segments(stream, bands, roses, vtoks):
    """Return [(run_indices, token_list)] segments, reading order.
    roses: [(cy, -cx, cx, s, v)] sorted; vtoks: [(s, v, [tokens])] in order."""
    band_of_cy = lambda cy: next((i for i, (y0, y1, _) in enumerate(bands)
                                  if y0 <= cy <= y1), None)
    rosb = [(band_of_cy(cy), cy, cx, s, v) for (cy, _n, cx, s, v) in roses]
    segs = []
    pending = []          # tokens of verses whose rosette is missing
    prev = None           # (band_idx, cx) of previous matched rosette
    ri = 0
    used = set()
    for s, v, toks in vtoks:
        block = pending + toks
        pending = []
        while ri < len(rosb) and (rosb[ri][3], rosb[ri][4]) != (s, v):
            ri += 1
        if ri >= len(rosb):
            pending = block   # no rosette: defer to next verse's segment
            continue
        rb_i, _rcy, rcx, _s, _v = rosb[ri]
        ridx = []
        if prev is None:
            for i in range(rb_i):
                ridx += [j for j, b in enumerate(stream) if b["line"] == i]
            ridx += [j for j, b in enumerate(stream)
                     if b["line"] == rb_i and b["cx"] > rcx]
        else:
            pb_i, _pcy, pcx = prev
            if rb_i == pb_i:
                ridx += [j for j, b in enumerate(stream)
                         if b["line"] == rb_i and pcx > b["cx"] > rcx]
            else:
                ridx += [j for j, b in enumerate(stream)
                         if b["line"] == pb_i and b["cx"] < pcx]
                for i in range(pb_i + 1, rb_i):
                    ridx += [j for j, b in enumerate(stream) if b["line"] == i]
                ridx += [j for j, b in enumerate(stream)
                         if b["line"] == rb_i and b["cx"] > rcx]
        ridx = sorted(set(ridx))
        used.update(ridx)
        segs.append((ridx, block))
        prev = (rb_i, rosb[ri][1], rcx)
        ri += 1
    if segs:
        lastr, lastt = segs[-1]
        extra = [j for j in range(len(stream)) if j not in used]
        segs[-1] = (lastr + extra, lastt)
    elif stream:
        segs.append((list(range(len(stream))),
                     [t for _, _, ts in vtoks for t in ts]))
    return segs


def main():
    verses = mt.load_tokens()
    tm = json.loads((DATA / "token_map2.json").read_text())
    spans = [tuple(tm["spans"][str(p + 1)]) if str(p + 1) in tm["spans"]
             else None for p in range(604)]
    off = {}
    first_sp = next((sp for sp in spans if sp), None)
    idx = sum(len(verses[i][2]) for i in range(first_sp[0]))
    for p in range(604):
        sp = spans[p]
        if sp is None:
            continue
        off[p + 1] = (idx, sum(len(verses[i][2])
                               for i in range(sp[0], sp[1] + 1)))
        idx += off[p + 1][1]
    roses = load_rosettes()
    out = []
    nfail = nskip = n1to1 = nseg = 0
    for p in range(604):
        sp = spans[p]
        if sp is None:
            continue
        page = p + 1
        s0, s1 = sp
        vtoks = [(verses[i][0], verses[i][1], verses[i][2])
                 for i in range(s0, s1 + 1)]
        toks = [t for _, _, ts in vtoks for t in ts]
        t0, nt = off[page]
        bands = page_bands(page)
        if bands is None or page not in roses:
            for k in range(nt):
                out.append(dict(t=t0 + k, page=page, boxes=[], skip=True))
                if bands is None:
                    pass
            continue
        stream = []
        for bi, (y0, y1, strip) in enumerate(bands):
            rr = band_runs(page, y0, y1)
            for b in rr:
                b["line"] = bi
                b["strip"] = int(strip)
                b["page"] = page
            stream.extend(rr)
        segs = build_segments(stream, bands, roses[page], vtoks)
        pos = 0
        for ridx, block in segs:
            nseg += 1
            runs = [stream[j] for j in ridx]
            res, nsk = assign_segment(runs, block)
            nskip += nsk
            if res is None:
                for k in range(len(block)):
                    out.append(dict(t=t0 + pos + k, page=page,
                                    boxes=[], skip=True))
                pos += len(block)
                continue
            for gi, g in enumerate(res):
                t = t0 + pos + gi
                pos += 1
                if not g:
                    out.append(dict(t=t, page=page, boxes=[], skip=True))
                    continue
                bs = [runs[j] for j in g]
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
    print(f"segments={nseg} failed={nfail} token-skips={nskip}")
    Path(DATA / "token_map3.json").write_text(json.dumps(
        dict(spans=tm["spans"], map=out)))
    print("saved token_map3.json;", len(out), "records")


if __name__ == "__main__":
    main()
