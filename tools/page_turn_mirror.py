"""Page-turn mirror rule test (A2b, S16): systematize S11's p154<->p155
strip mirror — do colored runs in the PAGE-BREAK bands (bottom band of
page p, top band of page p+1) align across the turn beyond null?

Nominal facing-pair reflection for (p even, p+1 odd): x_{p+1} = W - x_p.
The frame is 1024px; physical sheet registration has not been measured.
Metrics (run x-midpoints, tol = one 30px bin by default):
  x_mirror — |(W - x_p) - x_{p+1}| <= tol
  x_same   — |x_p - x_{p+1}| <= tol
Nulls:
  perm_x    — pool break-band runs corpus-wide, permute x among same
              band type (top/bottom), keep counts (ink-structure null).
  nonadj    — bottom(p) vs top(q), random q with |p-q|>2 (page-turn
              specificity).
  midband   — bottom(p) vs a random MIDDLE band of q (is the break
              position special at all?).
Also reports presence: P(break bands carry runs) for adjacent vs
non-adjacent pages.

Usage: python tools/page_turn_mirror.py [REPS] [TOL]
"""
import json
import argparse
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np
from rebuild_runs import page_bands
from audit_stats import tail_summary
from word_pair_census import pin_boxes, pin_manifest

DATA = Path(__file__).resolve().parent / "data"
W = 1024.0


def load_runs(src="mark_identity_semantic.json"):
    d = json.load(open(DATA / src))
    boxes = pin_boxes(src)
    last = {}
    for p in range(1, 605):
        if not (boxes / f"page_{p:03d}.json").exists():
            continue
        bands = page_bands(p, boxes=boxes)
        if bands:
            last[p] = len(bands) - 1
    by_pb = defaultdict(list)
    seen = set()
    for s in d["segments"]:
        for r in s.get("runs", []):
            pg = r.get("page", s["page"])
            key = (pg, r["band"], r["kind"], r["x0"], r["x1"])
            if pg not in last or key in seen:
                continue
            seen.add(key)
            by_pb[(pg, r["band"])].append(r)
    top = {p: by_pb[(p, 0)] for p in last}
    bot = {p: by_pb[(p, last[p])] for p in last}
    mid = {}
    for p in last:
        opts = list(range(1, last[p]))
        mid[p] = opts
    return top, bot, mid, by_pb


def hits(a_runs, b_runs, tol, mirror=True):
    n = 0
    for ra in a_runs:
        xa = (ra["x0"] + ra["x1"]) / 2.0
        if mirror:
            xa = W - xa
        for rb in b_runs:
            xb = (rb["x0"] + rb["x1"]) / 2.0
            if abs(xa - xb) <= tol:
                n += 1
    return n


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reps", type=int, nargs="?", default=1000)
    parser.add_argument("tol", type=float, nargs="?", default=30.0)
    parser.add_argument("--pairing", choices=("facing", "leaf", "adjacent"), default="facing")
    parser.add_argument("--output", type=Path, default=DATA / "audit_page_turn.json")
    parser.add_argument("--src", default="mark_identity_semantic.json")
    args = parser.parse_args()
    reps, tol = args.reps, args.tol
    if reps < 2 or tol < 0:
        parser.error("reps >= 2 and tol >= 0 required")
    top, bot, mid, by_pb = load_runs(args.src)
    rng = np.random.default_rng(41)
    pages = sorted(bot)
    pairs = [p for p in range(1, 604) if p in bot and p + 1 in top
             and (args.pairing == "adjacent" or p % 2 == (0 if args.pairing == "facing" else 1))]

    obs_m = obs_s = tot = 0
    for p in pairs:
        a, b = bot[p], top[p + 1]
        tot += len(a) * len(b)
        obs_m += hits(a, b, tol, mirror=True)
        obs_s += hits(a, b, tol, mirror=False)

    # --- null 1: permute x among break-band runs (same band type) ---
    bot_pages = sorted(bot)
    top_pages = sorted(top)
    bot_pool = [ (r["x0"] + r["x1"]) / 2.0 for p in bot_pages for r in bot[p] ]
    top_pool = [ (r["x0"] + r["x1"]) / 2.0 for p in top_pages for r in top[p] ]
    bot_len = {p: len(bot[p]) for p in bot_pages}
    top_len = {p: len(top[p]) for p in top_pages}
    nm, ns = np.empty(reps), np.empty(reps)
    for i in range(reps):
        bp = rng.permutation(bot_pool)
        tp = rng.permutation(top_pool)
        # re-assign x values in page order
        xbot, xtop = {}, {}
        k = 0
        for p in bot_pages:
            xbot[p] = bp[k:k + bot_len[p]]
            k += bot_len[p]
        k = 0
        for p in top_pages:
            xtop[p] = tp[k:k + top_len[p]]
            k += top_len[p]
        mi = si = 0
        for p in pairs:
            for xa in xbot[p]:
                xm = W - xa
                for xb in xtop[p + 1]:
                    if abs(xm - xb) <= tol:
                        mi += 1
                    if abs(xa - xb) <= tol:
                        si += 1
        nm[i] = mi
        ns[i] = si

    # --- null 2: non-adjacent control (random q) ---
    nm2, ns2 = np.empty(reps), np.empty(reps)
    controls = {p: np.array([q for q in pages if abs(q - p) > 2
                             and (args.pairing == "adjacent" or q % 2 == (p + 1) % 2)])
                for p in pairs}
    for i in range(reps):
        mi = si = 0
        for p in pairs:
            q = int(rng.choice(controls[p]))
            a, b = bot[p], top[q]
            mi += hits(a, b, tol, mirror=True)
            si += hits(a, b, tol, mirror=False)
        nm2[i] = mi
        ns2[i] = si

    # --- null 3: mid-band control ---
    nm3, ns3 = np.empty(reps), np.empty(reps)
    for i in range(reps):
        mi = si = 0
        for p in pairs:
            q = p + 1
            opts = mid.get(q)
            if not opts:
                continue
            b = by_pb[(q, opts[int(rng.choice(len(opts)))])]
            a = bot[p]
            mi += hits(a, b, tol, mirror=True)
            si += hits(a, b, tol, mirror=False)
        nm3[i] = mi
        ns3[i] = si

    def z(o, arr):
        mu, sd = float(arr.mean()), float(arr.std())
        return (o - mu) / sd if sd else None, mu, sd

    rep = dict(tol=tol, reps=reps, n_pairs=len(pairs),
               version="physical-break-bands-v2", pairing=args.pairing, seed=41,
               source=args.src,
               total_run_pairs=tot,
               obs_mirror=obs_m, obs_same=obs_s,
               perm_x_mirror=z(obs_m, nm), perm_x_same=z(obs_s, ns),
               nonadj_mirror=z(obs_m, nm2), nonadj_same=z(obs_s, ns2),
               midband_mirror=z(obs_m, nm3), midband_same=z(obs_s, ns3),
               perm_mu=(round(float(nm.mean()), 1), round(float(nm.std()), 1),
                        round(float(ns.mean()), 1), round(float(ns.std()), 1)),
               nonadj_mu=(round(float(nm2.mean()), 1), round(float(nm2.std()), 1),
                          round(float(ns2.mean()), 1), round(float(ns2.std()), 1)),
               midband_mu=(round(float(nm3.mean()), 1), round(float(nm3.std()), 1),
                           round(float(ns3.mean()), 1), round(float(ns3.std()), 1)))
    rep["inference"] = {name: tail_summary(obs, arr) for name, obs, arr in (
        ("perm_mirror", obs_m, nm), ("perm_same", obs_s, ns),
        ("nonadj_mirror", obs_m, nm2), ("nonadj_same", obs_s, ns2),
        ("midband_mirror", obs_m, nm3), ("midband_same", obs_s, ns3))}
    rep["inputs"] = pin_manifest(args.src)
    rep["null_samples"] = dict(perm_mirror=nm.tolist(), perm_same=ns.tolist(),
                               nonadj_mirror=nm2.tolist(), nonadj_same=ns2.tolist(),
                               midband_mirror=nm3.tolist(), midband_same=ns3.tolist())
    rep["caveat"] = "Selected colored runs; non-rejection is not proof of no mirror rule."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rep, indent=2) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k != "null_samples"}, indent=1))


if __name__ == "__main__":
    main()
