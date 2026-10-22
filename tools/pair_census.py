import json, sys
from pathlib import Path
from collections import defaultdict
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_stats import load_all, prep_slot_cloud
from type_rates import classify_types

DATA = Path(__file__).resolve().parent / "data"
NB = 32
W = 1024.0

# Farrin (2014) group layout, surah ranges
SYSTEM_A = [("a", 2, 5), ("b", 6, 9), ("c", 10, 15), ("d", 16, 21), ("e", 22, 24),
            ("d'", 25, 32), ("c'", 33, 39), ("b'", 40, 46), ("a'", 47, 49)]
CENTRAL = (50, 56)
SYSTEM_B = [("a", 57, 66), ("b", 67, 72), ("c", 73, 80), ("d", 81, 88), ("e", 89, 92),
            ("d'", 93, 98), ("c'", 99, 104), ("b'", 105, 108), ("a'", 109, 112)]

def group_of(s):
    for nm, lo, hi in SYSTEM_A + SYSTEM_B:
        if lo <= s <= hi:
            if nm.endswith("'"):
                base = nm[:-1]
                sysname = "A" if s <= 49 else "B"
                return f"{sysname}-{base}'"
            return ("A-" if s <= 49 else "B-") + nm
    if CENTRAL[0] <= s <= CENTRAL[1]:
        return "central"
    return None

def ring_pair(x, y):
    # 1: same letter-group correspondence (ring mirror within system, or system mirror)
    if x is None or y is None or x == "central" or y == "central":
        return None
    if x == y:
        return "same_group"
    def parse(g):
        sysname, nm = g.split("-")
        prime = nm.endswith("'")
        return sysname, nm[:-1] if prime else nm, prime
    sx, nx, px = parse(x)
    sy, ny, py = parse(y)
    if nx == ny and px != py:
        return "ring_mirror" if sx == sy else "system_mirror"
    return None

def load_words():
    d = np.load(DATA / "red_feats.npz")
    X, meta = d["X"], d["meta"]
    t, lab, deep, _ = classify_types()
    anchors = json.loads((DATA / "hayrat_surah_pages.json").read_text())
    starts = []
    for k, v in anchors.items():
        starts.append((v + 1, len(starts) + 1))
    starts.sort()

    def surah_of(page):
        s = 1
        for p0, idx in starts:
            if p0 <= page:
                s = idx
        return s

    pages = load_all()
    feats_by_page = defaultdict(list)
    for i in range(len(t)):
        feats_by_page[int(meta[i, 0])].append(i)
    key_of, word = {}, []
    for pg, ii in feats_by_page.items():
        for rank, i in enumerate(sorted(ii, key=lambda j: int(meta[j, 1]))):
            key_of[i] = (pg, rank)
    for i in range(len(t)):
        pg, jj = int(meta[i, 0]), int(meta[i, 1])
        r = json.loads((DATA / "real_boxes" / f"page_{pg:03d}.json").read_text())["reds"][jj]
        ty = t[i]
        if ty not in ("allah", "allah_pref", "rabbi", "huwa", "partner_word", "allah_signed"):
            continue
        word.append(dict(idx=i, page=pg, line=r["line"], cx=r["cx"], ty=ty,
                         s=surah_of(pg), g=group_of(surah_of(pg)),
                         x=X[i]))
    return word, pages

def main():
    word, pages = load_words()
    print(f"typed words: {len(word)}")
    P = np.array([w["page"] for w in word])
    L = np.array([w["line"] for w in word], dtype=np.int32)
    CX = np.array([w["cx"] for w in word])
    TY = np.array([w["ty"] for w in word])
    G = np.array([w["g"] for w in word])
    X = np.stack([w["x"] for w in word])
    order = np.argsort(P, kind="stable")
    P, L, CX, TY, G, X = P[order], L[order], CX[order], TY[order], G[order], X[order]
    odd = P % 2 == 1
    DB = np.where(odd, CX, W - CX)
    DB = np.clip((DB / 32.0).astype(np.int32), 0, NB - 1)

    # shape distance threshold: same-cluster percentile reference
    rng = np.random.default_rng(1)
    same_c, diff_c = [], []
    labs = np.load(DATA / "red_feats.npz")["lab"]
    labs = labs[order]
    for _ in range(4000):
        i, j = rng.integers(0, len(word), 2)
        if P[i] == P[j]:
            continue
        d = np.linalg.norm(X[i] - X[j])
        (same_c if labs[i] == labs[j] else diff_c).append(d)
    same_c, diff_c = np.array(same_c), np.array(diff_c)
    q = np.percentile(same_c, [5, 50]); qd = np.percentile(diff_c, [50, 90])
    print(f"shape dist: same p5={q[0]:.4f} p50={q[1]:.4f} | diff p50={qd[0]:.4f} p90={qd[1]:.4f}")

    # candidate same-type word pairs across pages (fixed set, shape-agnostic);
    # positional match is the variable part
    print("building candidate pairs (same type, different page)...")
    idx_by_ty_page = defaultdict(list)
    for i in range(len(word)):
        idx_by_ty_page[(TY[i], P[i])].append(i)
    cand_a, cand_b = [], []
    tys = sorted(set(TY))
    for ty in tys:
        pg_list = sorted({p for (t2, p) in idx_by_ty_page if t2 == ty})
        for ai, pa in enumerate(pg_list):
            for pb in pg_list[ai + 1:]:
                A = idx_by_ty_page[(ty, pa)]
                B = idx_by_ty_page[(ty, pb)]
                for i in A:
                    for j in B:
                        cand_a.append(i)
                        cand_b.append(j)
    cand_a = np.array(cand_a)
    cand_b = np.array(cand_b)
    print(f"same-type cross-page candidate pairs: {len(cand_a)}")

    def match_stats(lines, dbins, mask=None):
        m = (lines[cand_a] == lines[cand_b]) & (dbins[cand_a] == dbins[cand_b])
        if mask is not None:
            m &= mask
        pa, pb = P[cand_a][m], P[cand_b][m]
        return int(m.sum()), pa, pb

    # observed matches (all + shape-filtered)
    T = 0.030
    shape_ok = np.zeros(len(cand_a), dtype=bool)
    D = np.linalg.norm(X[cand_a] - X[cand_b], axis=1)
    shape_ok = D < T
    print(f"shape threshold T={T:.3f} -> candidate shape-similar pairs: {int(shape_ok.sum())}")
    n_all, pa_all, pb_all = match_stats(L, DB)
    n_sh, pa_sh, pb_sh = match_stats(L, DB, shape_ok)
    print(f"OBSERVED cross-page same-(line,dbin) matches: all={n_all}  shape-similar={n_sh}")

    # Farrin concordance of observed pairs
    def concord(pa, pb):
        gs = np.array([G[i] for i in range(len(word))])
        ga, gb = gs[cand_a], gs[cand_b]
        cls = []
        for k in range(len(cand_a)):
            r = ring_pair(ga[k], gb[k])
            if r is not None:
                cls.append(r)
        return np.array(cls)
    gs = np.array([w["g"] for w in word])
    ga, gb = gs[cand_a], gs[cand_b]
    ring = np.array([ring_pair(ga[k], gb[k]) is not None for k in range(len(cand_a))])
    cls = np.array([ring_pair(ga[k], gb[k]) or "none" for k in range(len(cand_a))])
    n_all_f, _, _ = match_stats(L, DB, ring)
    n_sh_f, _, _ = match_stats(L, DB, shape_ok & ring)
    print(f" Farrin-correspondent page-pairs: all={n_all_f}/{n_all}  shape-similar={n_sh_f}/{n_sh}")
    for cn in ["same_group", "ring_mirror", "system_mirror"]:
        cm = cls == cn
        nc, _, _ = match_stats(L, DB, cm)
        ncs, _, _ = match_stats(L, DB, cm & shape_ok)
        print(f"   {cn:13s} cands={int(cm.sum()):8d} matched={nc:5d} shape_matched={ncs:5d}")

    # null: random placement per page from slot cloud
    pagesl = load_all()
    reps = 200
    rng = np.random.default_rng(7)
    counts_by_page = defaultdict(int)
    for p in P:
        counts_by_page[p] += 1
    n_all_n, n_sh_n, n_all_f_n, n_sh_f_n = [], [], [], []
    cls_n = {cn: [] for cn in ["same_group", "ring_mirror", "system_mirror"]}
    cls_ns = {cn: [] for cn in ["same_group", "ring_mirror", "system_mirror"]}
    for r in range(reps):
        lines = L.copy()
        dbins = DB.copy()
        for p in sorted(set(P.tolist())):
            ii = np.where(P == p)[0]
            k = len(ii)
            if p not in pagesl:
                # keep original (page not usable) - rare
                continue
            d = pagesl[p]
            sline, sbin, _ = prep_slot_cloud(d["slots"], d["nlines"])
            pick = rng.choice(len(sline), size=k, replace=False)
            lines[ii] = sline[pick]
            cxs = d["slots"][pick, 1]
            dbins[ii] = np.clip(((cxs if p % 2 == 1 else W - cxs) / 32.0).astype(np.int32), 0, NB - 1)
        na, _, _ = match_stats(lines, dbins)
        ns, _, _ = match_stats(lines, dbins, shape_ok)
        nf, _, _ = match_stats(lines, dbins, ring)
        nsf, _, _ = match_stats(lines, dbins, shape_ok & ring)
        n_all_n.append(na)
        n_sh_n.append(ns)
        n_all_f_n.append(nf)
        n_sh_f_n.append(nsf)
        for cn in cls_n:
            cm = cls == cn
            nc, _, _ = match_stats(lines, dbins, cm)
            ncs, _, _ = match_stats(lines, dbins, cm & shape_ok)
            cls_n[cn].append(nc)
            cls_ns[cn].append(ncs)
    for nm, obs, nl in [("all", n_all, n_all_n), ("shape", n_sh, n_sh_n),
                        ("all+Farrin", n_all_f, n_all_f_n), ("shape+Farrin", n_sh_f, n_sh_f_n)]:
        nl = np.array(nl)
        z = (obs - nl.mean()) / (nl.std() or 1)
        print(f"NULL {nm:13s} obs={obs:4d} null={nl.mean():7.1f}±{nl.std():5.1f} "
              f"z={z:6.2f} P>={float((nl >= obs).mean()):.4g}")
    for cn in cls_n:
        nl = np.array(cls_n[cn]); nls = np.array(cls_ns[cn])
        nc, _, _ = match_stats(L, DB, cls == cn)
        ncs, _, _ = match_stats(L, DB, (cls == cn) & shape_ok)
        zc = (nc - nl.mean()) / (nl.std() or 1)
        zs = (ncs - nls.mean()) / (nls.std() or 1)
        print(f"NULL {cn:13s} obs={nc:4d} null={nl.mean():7.1f}±{nl.std():5.1f} z={zc:5.1f} | "
              f"shape obs={ncs:4d} null={nls.mean():6.1f}±{nls.std():4.1f} z={zs:5.1f}")

    # central group test: per-page alignment rate pages 518-536 (surah 50-56)
    print()
    print("CENTRAL GROUP test (surah 50-56 = pages 518-536):")
    flags = {}
    prev = None
    for p in sorted(set(P.tolist())):
        if p not in pagesl:
            continue
        ii = np.where(P == p)[0]
        d = pagesl[p]
        nlines = d["nlines"]
        lines = L[ii]
        cbins = np.clip(((CX[ii] - 26.0) / 30.0).astype(np.int32), 0, NB - 1)
        dbins = DB[ii]
        lb = np.zeros((nlines, NB), dtype=np.int32)
        np.add.at(lb, (lines, cbins), 1)
        tot = lb.sum(axis=0)
        col = tot[cbins] >= 2
        col &= (tot[cbins] - lb[lines, cbins]) >= 1
        mir = np.zeros(len(ii), dtype=bool)
        if prev is not None:
            pl, pd, pnl = prev
            nl2 = max(nlines, pnl)
            ma = np.zeros((nl2, NB), dtype=np.int32)
            mb = np.zeros((nl2, NB), dtype=np.int32)
            np.add.at(ma, (lines, dbins), 1)
            np.add.at(mb, (pl, pd), 1)
            mir = ma[lines, dbins] & mb[lines, dbins]
        for k, i in enumerate(ii):
            flags[i] = bool(col[k] or mir[k])
        prev = (lines, dbins, nlines)
    cen = [i for i in range(len(word)) if CENTRAL[0] <= word[i]["s"] <= CENTRAL[1] and i in flags]
    oth = [i for i in range(len(word)) if not (CENTRAL[0] <= word[i]["s"] <= CENTRAL[1]) and i in flags]
    rc = np.mean([flags[i] for i in cen]) if cen else 0
    ro = np.mean([flags[i] for i in oth]) if oth else 0
    print(f"  central 50-56: {np.mean([flags[i] for i in cen])*100:.1f}% aligned (n={len(cen)})")
    print(f"  rest:          {np.mean([flags[i] for i in oth])*100:.1f}% aligned (n={len(oth)})")
    # two-proportion z
    import math
    p1, n1 = sum(flags[i] for i in cen), len(cen)
    p0, n0 = sum(flags[i] for i in oth), len(oth)
    pp = (p1 + p0) / (n1 + n0)
    se = math.sqrt(pp * (1 - pp) * (1 / n1 + 1 / n0))
    print(f"  z = {(p1/n1 - p0/n0)/se:.2f}")

if __name__ == "__main__":
    main()