import json, re, sys
import numpy as np
from collections import Counter

sys.path.insert(0, ".")
from tools.prob_model import load, pack, layout, col_stat, pair_matches, L_LINES, WIDTH

FAMS = {
    "الله": lambda t: t == "الله",
    "رب*": lambda t: t.startswith("رب") and t not in ("ربا",),
    "هو": lambda t: t == "هو",
    "رحيم*": lambda t: "رحيم" in t,
    "الرحمن*": lambda t: "رحمن" in t,
    "غفور*": lambda t: "غفور" in t,
    "الملك": lambda t: t == "الملك",
    "محمد": lambda t: t in ("محمد", "احمد"),
    "ذكر*": lambda t: t.startswith("ذكر") or t.startswith("اذك"),
}

def main():
    pages = pack(load(), L_LINES * WIDTH * 0.999,
                 char_w := ((L_LINES * WIDTH * 604 - 6236 * 10.0
                             - 6.0 * sum(len(t) for _, toks in load() for t in toks))
                            / sum(len(t) for _, toks in load() for t in toks)))
    slots = layout(pages)
    pg = np.array([s[0] for s in slots])
    ln = np.array([s[1] for s in slots])
    xx = np.array([s[2] for s in slots])
    toks = [s[3] for s in slots]
    rng = np.random.default_rng(21)
    N = len(slots)
    print(f"{'family':8s} {'n':>5s} {'asifreal':>8s}  null colmax percentiles and thresholds")
    for name, pred in FAMS.items():
        mask = np.array([pred(t) for t in toks])
        n = int(mask.sum())
        if n == 0:
            print(f"{name:8s} {0:5d}  ---")
            continue
        cm, per = col_stat(pg[mask], xx[mask])
        reps = 5000 if n > 50 else 30000
        cmax = np.empty(reps, dtype=np.int32)
        for r in range(reps):
            idx = rng.choice(N, size=min(n, N), replace=False)
            cmax[r], _ = col_stat(pg[idx], xx[idx])
        q = np.percentile(cmax, [50, 99])
        thr = None
        for k in range(2, 15):
            if float((cmax >= k).mean()) < 1e-3:
                thr = k
                break
        print(f"{name:8s} {n:5d} {cm:8d}   p50={q[0]:.0f} p99={q[1]:.0f} "
              f"min-surprising-col(k, p<1e-3)={thr}  maxseen={cmax.max()}")

if __name__ == "__main__":
    main()
