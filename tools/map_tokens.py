import json, re, sys
from pathlib import Path
import numpy as np

DATA = Path(__file__).resolve().parent / "data" / "real_boxes"
TOKENS_F = Path(__file__).resolve().parent / "data" / "quran-uthmani.json"
NB, W = 32, 1024.0
G, LAMB, LAMT = 10, 0.60, 3.0
WCOST = 4.0

DIAC = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED\u0653-\u0655\u0640]")

def norm(t):
    t = DIAC.sub("", t)
    return (t.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا")
             .replace("آ", "ا").replace("ى", "ي").replace("ة", "ه"))

def load_tokens():
    d = json.load(open(TOKENS_F))
    verses = []
    for v in d["verses"]:
        s, a = v["verse_key"].split(":")
        toks = [norm(t) for t in v["text_uthmani"].split() if norm(t)]
        verses.append((int(s), int(a), toks))
    return verses

def est_width(tok):
    if not hasattr(est_width, "model"):
        f = DATA.parent / "letter_model.json"
        est_width.model = json.loads(f.read_text()) if f.exists() else None
    m = est_width.model
    if m is None:
        if len(tok) <= 1:
            return 24.0
        return 22.0 + 11.5 * len(tok)
    wm = m["width"]
    w = wm["intercept"]
    for c in tok:
        w += wm.get(c, 8.5)
    w += wm["diac"] * (len(tok) - len(DIAC.sub("", tok)))
    return max(16.0, w)

def load_page(n, keep_strips=False):
    """Returns (page_json, stream). Slots with line=None (strips / grid-fail
    zones) are dropped unless keep_strips=True, in which case they are
    clustered into y-bands, flagged strip=1, and the whole stream is
    renumbered in y order (safe: page_dp is order-based, never uses line)."""
    f = DATA / f"page_{n:03d}.json"
    if not f.exists():
        return None
    d = json.loads(f.read_text())
    if d["grid"] is None:
        return None
    lines = {}
    strips = []
    for s in d["slots"]:
        if s["color"] == "gold":
            continue
        s = dict(s)
        s["body"] = 1 if (s["y1"] - s["y0"] + 1 >= 22 or s["npx"] >= 150) else 0
        if s["line"] is None:
            if keep_strips:
                s["strip"] = 1
                strips.append(s)
            continue
        s["strip"] = 0
        lines.setdefault(s["line"], []).append(s)
    if keep_strips and strips:
        strips.sort(key=lambda c: (c["y0"] + c["y1"]) / 2)
        bands = []
        for c in strips:
            cy = (c["y0"] + c["y1"]) / 2
            if bands and cy - bands[-1][0] < 60:
                bands[-1][0] = cy
                bands[-1][1].append(c)
            else:
                bands.append([cy, [c]])
        units = [(cy, grp) for cy, grp in bands]
        for li, ss in lines.items():
            cy = (min(c["y0"] for c in ss) + max(c["y1"] for c in ss)) / 2
            units.append((cy, ss))
        units.sort(key=lambda u: u[0])
        renum = {}
        for cy, grp in units:
            renum[len(renum)] = grp
        lines = renum
        # split any line whose slots form disjoint y-bands (e.g. the bottom
        # strip sharing line 14 with the last grid line on p154) into
        # sub-lines in y order — page_dp needs one band per line
        out = {}
        for li, ss in lines.items():
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
                out[len(out)] = grp
        lines = out
    stream = []
    for li in sorted(lines):
        cs = sorted(lines[li], key=lambda c: -c["x1"])
        bodies = [c for c in cs if c["body"]]
        frags = [c for c in cs if not c["body"]]
        merged = [dict(x0=c["x0"], x1=c["x1"], y0=c["y0"], y1=c["y1"],
                       cx=c["cx"], cy=c["cy"], npx=c["npx"], line=li,
                       color=c["color"], strip=c.get("strip", 0)) for c in bodies]
        for f in frags:
            best, bo = None, -1
            for m in merged:
                ov = min(f["x1"], m["x1"]) - max(f["x0"], m["x0"])
                if ov > bo:
                    bo, best = ov, m
            if bo >= 0 or True:
                cand = [m for m in merged
                        if (m["x0"] - f["x1"] <= 14 and f["x0"] - m["x1"] <= 14)]
                if cand:
                    best = max(cand, key=lambda m: min(f["x1"], m["x1"]) - max(f["x0"], m["x0"]))
            if best is not None and bo >= 0:
                best["x0"] = min(best["x0"], f["x0"])
                best["x1"] = max(best["x1"], f["x1"])
                best["y0"] = min(best["y0"], f["y0"])
                best["y1"] = max(best["y1"], f["y1"])
                best["npx"] += f["npx"]
        stream.extend(sorted(merged, key=lambda c: -c["x1"]))
    return d, stream

def span_dp(verses, page_mass, anchors, kmax=28):
    tok_cum_v = np.concatenate([[0.0], np.cumsum(
        [float(len(ts)) for _, _, ts in verses])])
    nv, npages = len(verses), len(page_mass)
    mm = np.array([m if m is not None else np.nan for m in page_mass],
                  dtype=np.float64)
    idx = np.arange(len(mm))
    good = ~np.isnan(mm)
    mm = np.interp(idx, idx[good], mm[good])
    scale = tok_cum_v[-1] / mm.sum()
    targets = mm * scale
    a_min = {}
    a_max = {}
    for page, u in anchors:
        a_min[page] = min(a_min.get(page, 10 ** 9), u)
        a_max[page] = max(a_max.get(page, -1), u)
    INF = 1e15
    D = np.full((npages + 1, nv + 1), INF)
    PD = np.full((npages + 1, nv + 1), -1, dtype=np.int16)
    D[0, 0] = 0.0
    varr = np.arange(nv, dtype=np.int64)
    for p in range(npages):
        row = D[p]
        finite = row < INF / 2
        if not finite.any():
            return None
        tgt = targets[p]
        if p + 1 in a_min:
            fin2 = finite.copy()
            fin2[a_min[p + 1] + 1:] = False
            finite = fin2
        for delta in range(1, kmax + 1):
            v_hi = nv - delta
            if v_hi < 0:
                break
            src = row[:v_hi + 1]
            ok = finite[:v_hi + 1]
            if not ok.any():
                continue
            got = tok_cum_v[delta:v_hi + delta + 1] - tok_cum_v[:v_hi + 1]
            if tgt > 0:
                cost = ((tgt - got) / max(0.25 * tgt, 16.0)) ** 2 * 1e3
            else:
                cost = np.zeros(v_hi + 1)
            cand = np.where(ok, src + cost, INF)
            if p + 1 in a_max:
                u = a_max[p + 1]
                lo = max(0, u + 1 - delta)
                cand[:lo] = INF
            dst = D[p + 1, delta:nv + 1]
            upd = cand < dst[:v_hi + 1]
            dst[:v_hi + 1][upd] = cand[upd]
            sl = PD[p + 1, delta:nv + 1]
            sl[upd] = delta
    if D[npages, nv] >= INF / 2:
        return None
    spans = [None] * npages
    v = nv
    for p in range(npages, 0, -1):
        delta = int(PD[p, v])
        spans[p - 1] = (v - delta, v)
        v = v - delta
    return spans, float(D[npages, nv])

def page_dp(stream, toks, jit=None):
    n, m = len(stream), len(toks)
    if n == 0 or m == 0:
        return None, None
    x1 = np.array([b["x1"] for b in stream], dtype=np.float64)
    x0 = np.array([b["x0"] for b in stream], dtype=np.float64)
    wseg = x1 - x0 + 1
    cumw = np.concatenate([[0.0], np.cumsum(wseg)])
    body = np.array([1 if (b["y1"] - b["y0"] + 1 >= 22 or b["npx"] >= 150) else 0
                     for b in stream], dtype=np.int32)
    cumb = np.concatenate([[0], np.cumsum(body)])
    est = np.array([est_width(t) for t in toks])
    cume = np.concatenate([[0.0], np.cumsum(est)])
    INF = 1e12
    D = np.full((m + 1, n + 1), INF)
    PI = np.full((m + 1, n + 1), -2, dtype=np.int16)
    PJ = np.full((m + 1, n + 1), -2, dtype=np.int16)
    D[0, 0] = 0.0
    pmarg = np.arange(n + 1, dtype=np.float64) * LAMB
    PMV = np.zeros(m + 1, dtype=np.int32)
    for i in range(m + 1):
        row = D[i]
        fin = np.where(row < INF / 2)[0]
        if len(fin) == 0:
            continue
        base = np.full(n + 1, INF)
        base[fin] = row[fin] - LAMB * fin
        cummin = np.minimum.accumulate(base)
        rec = np.where(base == cummin)[0]
        if len(rec):
            j0s = rec[np.searchsorted(rec, np.arange(n + 1), side="right") - 1]
            j0s = np.clip(j0s, 0, n)
            Dsh = np.where(cummin < INF / 2, cummin + pmarg, INF)
            upd_sb = (Dsh < row - 1e-9) & (j0s < np.arange(n + 1))
            D[i, :] = np.where(upd_sb, Dsh, row)
            PI[i, :] = np.where(upd_sb, i, PI[i, :])
            PJ[i, :] = np.where(upd_sb, j0s, PJ[i, :])
        if i == m:
            continue
        if i < m:
            src = D[i]
            tgt = D[i + 1]
            upd = src + LAMT < tgt
            D[i + 1] = np.where(upd, src + LAMT, tgt)
            PI[i + 1] = np.where(upd, i, PI[i + 1])
            PJ[i + 1] = np.where(upd, np.arange(n + 1), PJ[i + 1])
            for g in range(1, G + 1):
                if g > n:
                    break
                srcj = np.arange(0, n + 1 - g)
                base2 = D[i, srcj]
                got = cumw[srcj + g] - cumw[srcj]
                span = x1[srcj] - x0[srcj + g - 1] + 1
                width = np.maximum(span, got * 0.65) + 6.0 * (g - 1)
                wc = np.abs(width - est[i]) / max(est[i], 24.0)
                cand = base2 + wc * WCOST + 0.08 * (g - 1)
                has_body = (cumb[srcj + g] - cumb[srcj]) >= 1
                cand = np.where(has_body, cand, INF)
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
    verses = load_tokens()
    tokens = [(s, a, t) for s, a, ts in verses for t in ts]
    tok_verse = [i for i, (_, _, ts) in enumerate(verses) for _ in ts]
    ntok = len(tokens)
    sig_slots, sig_mass, sig_width = [], [], []
    for n in range(1, 605):
        lp = load_page(n)
        if lp is None:
            sig_slots.append(None); sig_mass.append(None); sig_width.append(None)
            continue
        d, stream = lp
        sig_slots.append(float(len(stream)))
        sig_mass.append(float(sum(c["npx"] for c in stream)))
        sig_width.append(float(d["grid"]["n_bands"]) * 880.0)
    import numpy as _np
    sc = ntok / _np.nansum(_np.array([s if s is not None else _np.nan for s in sig_slots]))
    mc = ntok / _np.nansum(_np.array([m if m is not None else _np.nan for m in sig_mass]))
    wc = ntok / _np.nansum(_np.array([w if w is not None else _np.nan for w in sig_width]))
    page_budget = []
    for s, m, w in zip(sig_slots, sig_mass, sig_width):
        vals = [v * k for v, k in ((s, sc), (m, mc), (w, wc)) if v is not None]
        page_budget.append(float(_np.mean(vals)) if vals else None)
    vidx = [0]
    for i, (s_, a_, ts) in enumerate(verses):
        if a_ == 1 and i > 0:
            vidx.append(i)
    sur2 = json.load(open(Path(__file__).resolve().parent / "data" / "hayrat_surah_pages_v2.json"))
    def start_page(s):
        if s == 1 or s == 2:
            return 1
        if s == 9:
            return 186
        return sur2[f"surah_{s}"] + 1
    anchors = []
    for s in range(1, 115):
        page = start_page(s)
        if 1 <= page <= 604:
            anchors.append((page, vidx[s - 1]))
    spans, cost = span_dp(verses, page_budget, anchors)
    print("span DP cost:", round(cost, 2))
    for p in (206, 207, 421, 422):
        a, b = spans[p]
        print(f"  anchor check p{p}: {verses[a][0]}:{verses[a][1]}..{verses[b-1][0]}:{verses[b-1][1]}")
    out = []
    tok_idx = 0
    total_wres = []
    for p in range(604):
        s0, s1 = spans[p]
        ntok = sum(len(verses[i][2]) for i in range(s0, s1))
        lp = load_page(p + 1)
        if lp is None:
            tok_idx += ntok
            continue
        d, stream = lp
        toks = [t for i in range(s0, s1) for t in verses[i][2]]
        cost, mapping = page_dp(stream, toks)
        if mapping is None:
            print(f"page {p+1}: DP FAILED ({len(stream)} boxes vs {ntok} toks)")
            tok_idx += ntok
            continue
        nskipb = n - sum(len(g) for g in mapping if g)
        nskipt = sum(1 for g in mapping if not g)
        for gi, g in enumerate(mapping):
            if g is None or len(g) == 0:
                out.append(dict(t=tok_idx, page=p + 1, boxes=[], skip=True))
            else:
                bs = [stream[j] for j in g]
                out.append(dict(t=tok_idx, page=p + 1,
                                boxes=[b["cx"] for b in bs],
                                x=[min(b["x0"] for b in bs), max(b["x1"] for b in bs)],
                                line=bs[0]["line"],
                                n=len(bs),
                                npx=sum(b["npx"] for b in bs),
                                span=bs[0]["x1"] - bs[-1]["x0"] + 1))
                wres = abs((bs[0]["x1"] - bs[-1]["x0"] + 1) - est_width(toks[gi]))
                total_wres.append(wres / max(est_width(toks[gi]), 24.0))
            tok_idx += 1
        if (p + 1) % 100 == 0:
            print(f"page {p+1}: {len(stream)} boxes, {ntok} toks, "
                  f"skipB={nskipb} skipT={nskipt} cost={cost:.1f}")
    print("mean width residual:", round(float(np.mean(total_wres)), 3))
    Path("tools/data/token_map.json").write_text(json.dumps(
        dict(spans={str(k + 1): v for k, v in enumerate(spans)},
             map=out)))
    print("saved", len(out), "token records")

if __name__ == "__main__":
    main()

def refine_spans(verses, anchors, spans0, win=2, dev_pen=4.0, cache={}):
    nv = len(verses)
    a_min, a_max = {}, {}
    for page, u in anchors:
        a_min[page] = min(a_min.get(page, 10 ** 9), u)
        a_max[page] = max(a_max.get(page, -1), u)
    usable = {p: load_page(p + 1) for p in range(604)}
    def pcost(p, a, b):
        key = (p, a, b)
        if key in cache:
            return cache[key]
        if b - a < 1:
            cache[key] = 1e9
            return 1e9
        lp = usable.get(p)
        if lp is None:
            c = 0.0
        else:
            toks = [t for i in range(a, b) for t in verses[i][2]]
            res = page_dp(lp[1], toks)
            c = res[0] if res[0] is not None else 400.0
        c += dev_pen * (abs(a - spans0[p][0]) + abs(b - spans0[p][1]))
        cache[key] = c
        return c
    col = {0: (0.0, -1)}
    trace = []
    for p in range(604):
        s0, s1 = spans0[p]
        cands_a = [a for a in range(max(0, s0 - win), s0 + win + 1) if a in col]
        cands_b = range(max(1, s1 - win), min(nv, s1 + win) + 1)
        newcol = {}
        for b in cands_b:
            if p + 1 in a_min and b <= a_min[p + 1]:
                continue
            best = None
            for a in cands_a:
                if p in a_min and a > a_min[p]:
                    continue
                if p in a_max and b <= a_max[p]:
                    continue
                c = col[a][0] + pcost(p, a, b)
                if best is None or c < best[0]:
                    best = (c, a)
            if best is not None:
                newcol[b] = best
        if not newcol:
            newcol = {s1: (col.get(s0, (0.0, -1))[0], s0)}
        col = newcol
        trace.append(col)
    b = nv
    if nv not in trace[603]:
        cand = min(trace[603], key=lambda v: abs(v - nv))
        b = cand
    spans = [None] * 604
    for p in range(603, -1, -1):
        c, a = trace[p][b]
        spans[p] = (a, b)
        b = a
    return spans
