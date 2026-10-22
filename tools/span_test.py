import json, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from map_tokens import load_tokens, load_page, DIAC

NB, W = 32, 1024.0
DATA = Path(__file__).resolve().parent / "data"

def span_dp_generic(page_target, tok_cum_v, anchors, kmax=30, tol=0.25, floor=16.0):
    nv, npages = len(tok_cum_v) - 1, len(page_target)
    mm = np.array([t if t is not None else np.nan for t in page_target], dtype=np.float64)
    idx = np.arange(len(mm))
    good = ~np.isnan(mm)
    mm = np.interp(idx, idx[good], mm[good])
    scale = tok_cum_v[-1] / mm.sum()
    targets = mm * scale
    a_min, a_max = {}, {}
    for page, u in anchors:
        a_min[page] = min(a_min.get(page, 10**9), u)
        a_max[page] = max(a_max.get(page, -1), u)
    INF = 1e15
    D = np.full((npages + 1, nv + 1), INF)
    PD = np.full((npages + 1, nv + 1), -1, dtype=np.int16)
    D[0, 0] = 0.0
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
                cost = ((tgt - got) / max(tol * tgt, floor)) ** 2 * 1e3
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
    return spans

def em_budget(verses, base_signal, anchors, iters=3, kmax=30, smooth=12):
    tok_counts = np.array([len(ts) for _, _, ts in verses], dtype=np.float64)
    tok_cum = np.concatenate([[0.0], np.cumsum(tok_counts)])
    sig = np.array([s if s is not None else np.nan for s in base_signal])
    idx = np.arange(len(sig))
    sig = np.interp(idx, idx[~np.isnan(sig)], sig[~np.isnan(sig)])
    # global ratio start
    ratio = np.full(len(sig), tok_cum[-1] / sig.sum())
    spans = None
    for it in range(iters):
        targets = sig * ratio
        spans = span_dp_generic(list(targets), tok_cum, anchors, kmax=kmax)
        # implied tokens per page
        imp = np.zeros(len(spans))
        for p, (a, b) in enumerate(spans):
            imp[p] = tok_cum[b] - tok_cum[a]
        # local ratio: tokens per unit signal, smoothed
        r = np.where(sig > 0, imp / np.maximum(sig, 1e-9), ratio)
        # smooth in log domain over page-neighbors with signal>0
        lr = np.log(np.maximum(r, 1e-3))
        kernel = np.ones(2 * smooth + 1)
        num = np.convolve(lr * (imp > 0), kernel, mode="same")
        den = np.convolve((imp > 0).astype(float), kernel, mode="same")
        sm = np.where(den > 0, num / np.maximum(den, 1), lr)
        ratio = np.exp(sm)
        ratio = np.clip(ratio, 0.4 * ratio.mean(), 2.5 * ratio.mean())
    return spans, ratio

def vk(spans, p, verses):
    a, b = spans[p]
    return f"p{p}->{verses[a][0]}:{verses[a][1]}..{verses[b-1][0]}:{verses[b-1][1]}"

def main():
    verses = load_tokens()
    sur = json.load(open(DATA / "hayrat_surah_pages.json"))
    vidx = [0]
    for i, (s_, a_, ts) in enumerate(verses):
        if a_ == 1 and i > 0:
            vidx.append(i)
    anchors = []
    for k, (label, rp) in enumerate(sur.items()):
        if k >= 94:
            break
        page = rp + 1
        if 2 <= page <= 604:
            anchors.append((page, vidx[k]))
    slots, mass = [], []
    for n in range(1, 605):
        lp = load_page(n)
        if lp is None:
            slots.append(None)
            mass.append(None)
        else:
            d, stream = lp
            slots.append(len(stream))
            mass.append(sum(c["npx"] for c in stream))
    truth = {206: "9:129 (end)", 207: "10:1 (start)",
             421: "~33:41 zone", 422: "starts ~33:36", 423: "33:37+"}
    import map_tokens as mt
    estw = [sum(mt.est_width(t) for t in ts) for _, _, ts in verses]
    tok_cum_w = np.concatenate([[0.0], np.cumsum(estw)])
    anchors_d = {}
    for page, u in anchors:
        anchors_d.setdefault(page, [10**9, -1])
        anchors_d[page][0] = min(anchors_d[page][0], u)
        anchors_d[page][1] = max(anchors_d[page][1], u)
    lines = []
    for n in range(1, 605):
        lp = load_page(n)
        if lp is None:
            lines.append(None)
        else:
            lines.append(lp[0]["grid"]["n_bands"])
    lines = np.array([l if l is not None else np.nan for l in lines], dtype=np.float64)
    idx = np.arange(len(lines))
    lines = np.interp(idx, idx[~np.isnan(lines)], lines[~np.isnan(lines)])
    # width budget: sum of est_width on page ~ nlines * avg line width
    # estimate avg line width from pages with many slots: total span of boxes per line ~ 880
    wtarget = lines * 880.0
    wtarget = wtarget * (tok_cum_w[-1] / np.nansum(wtarget))

    def run(tok_cum, tgt_list, tol=0.25, floor=16.0):
        tgt = [t if t is not None and t == t else None for t in tgt_list]
        return span_dp_generic(tgt, tok_cum, anchors, kmax=30, tol=tol, floor=floor)

    def show(nm, spans):
        print(f"{nm}: " + " ".join(vk(spans, p, verses) for p in (206, 207, 421, 422)))

    tok_cum_c = np.concatenate([[0.0], np.cumsum([float(len(ts)) for _, _, ts in verses])])
    show("width-budget", run(tok_cum_w, list(wtarget), tol=0.15, floor=150.0))
    s_sp = run(tok_cum_c, slots)
    show("slots", s_sp)
    m_sp = run(tok_cum_c, mass)
    show("mass", m_sp)
    # combined: average of token-equivalent budgets
    def mean_ignore_none(vals):
        vals = [v for v in vals if v is not None]
        return float(np.mean(vals)) if vals else None
    sc = tok_cum_c[-1] / np.nansum(np.array([s if s is not None else np.nan for s in slots]))
    mc = tok_cum_c[-1] / np.nansum(np.array([m if m is not None else np.nan for m in mass]))
    wc = tok_cum_c[-1] / np.nansum(wtarget)
    comb = []
    for i in range(604):
        s = slots[i] * sc if slots[i] is not None else None
        m = mass[i] * mc if mass[i] is not None else None
        w = wtarget[i] * wc if not np.isnan(wtarget[i]) else None
        vals = [v for v in (s, m, w) if v is not None]
        comb.append(np.mean(vals) if vals else None)
    show("combined", run(tok_cum_c, comb))
    # pair combos
    for nm in [("slots+width",), ("mass+width",), ("slots+mass",), ("all3",)]:
        nm = nm[0]
        c2 = []
        for i in range(604):
            s = slots[i] * sc if slots[i] is not None else None
            m = mass[i] * mc if mass[i] is not None else None
            w = wtarget[i] * wc if not np.isnan(wtarget[i]) else None
            parts = []
            if "slots" in nm and s is not None: parts.append(s)
            if "mass" in nm and m is not None: parts.append(m)
            if "width" in nm and w is not None: parts.append(w)
            if nm == "all3":
                parts = [v for v in (s, m, w) if v is not None]
            c2.append(np.mean(parts) if parts else None)
        show(nm, run(tok_cum_c, c2))

if __name__ == "__main__":
    main()