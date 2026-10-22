"""Edge-vs-design test: do SAME-TOKEN pins land at the same cell across
pages more than token-shuffled nulls predict? (S13 next-step 2.)

Pins = count-matched run<->token pairs from mark_identity full blocks
(cri class: divine-name words with token identity; 1,856 pins).

Cell = (band, x0//30) as in census v3 (band ~ page-local y-row index).
Cross-page pairs only. Null B: globally permute token labels among pins
(preserves token counts, destroys word<->position association). R reps.
Report: same-token same-cell pairs obs vs null, z, plus per-token and
per-xbin breakdowns (edge vs center vs middle).

Usage: python tools/pin_align_test.py [REPS=200]
"""
import json
import sys
from collections import Counter, defaultdict

import numpy as np

REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 200
rng = np.random.default_rng(7)


def cell(p):
    return (p["band"], p["x0"] // 30)


def load_pins():
    d = json.load(open("tools/data/mark_identity.json"))
    pins = [p for s in d["segments"] if s["verdict"] == "full"
            for p in s["pins"] if p["kind"] == "cri"]
    return pins


def pair_counts(pins, toks):
    """Cross-page same-cell pairs; returns (same_tok, diff_tok, all)."""
    by_cell = defaultdict(list)
    for p, tk in zip(pins, toks):
        by_cell[cell(p)].append(tk)
    same = diff = 0
    for c, group in by_cell.items():
        n = len(group)
        if n < 2:
            continue
        # cross-page pairs: group entries are pins on >=1 pages; count pairs
        # with distinct pages
        idx = list(range(n))
        # need pages; recompute via zip order — pass pages too
    return None


def pair_counts_full(pins, toks):
    by_cell = defaultdict(list)  # cell -> list of (page, tok)
    for p, tk in zip(pins, toks):
        by_cell[cell(p)].append((p["page"], tk))
    same = diff = tot = 0
    same_pairs = Counter()
    for c, group in by_cell.items():
        n = len(group)
        for i in range(n):
            for j in range(i + 1, n):
                if group[i][0] == group[j][0]:
                    continue
                tot += 1
                if group[i][1] == group[j][1]:
                    same += 1
                    same_pairs[group[i][1]] += 1
                else:
                    diff += 1
    return same, diff, tot, same_pairs


def main():
    pins = load_pins()
    toks = [p["tok"] for p in pins]
    print(f"pins={len(pins)} tokens={Counter(toks).most_common(5)}")
    obs_same, obs_diff, obs_tot, obs_pairs = pair_counts_full(pins, toks)
    print(f"obs: same-cell same-token={obs_same} diff-token={obs_diff} "
          f"total={obs_tot} (same share {obs_same/max(obs_tot,1):.3f})")
    print("obs same-token pairs by token:", obs_pairs.most_common(8))
    # null B: global token permutation
    null_same = []
    tarr = np.array(toks, dtype=object)
    for _ in range(REPS):
        perm = rng.permutation(len(toks))
        sh = tarr[perm].tolist()
        s_, _d, _t, _sp = pair_counts_full(pins, sh)
        null_same.append(s_)
    null_same = np.array(null_same)
    mu, sd = null_same.mean(), null_same.std()
    z = (obs_same - mu) / sd if sd else 0.0
    print(f"null same-token same-cell pairs: {mu:.1f} +- {sd:.1f} "
          f"(REPS={REPS}) -> z={z:+.1f}")
    # per-xbin breakdown of same-cell pairs
    pins_x = defaultdict(list)
    for p, tk in zip(pins, toks):
        pins_x[(p["band"], p["x0"] // 30)].append((p["page"], tk))
    same_x = Counter()
    for c, group in pins_x.items():
        n = len(group)
        for i in range(n):
            for j in range(i + 1, n):
                if group[i][0] != group[j][0] and group[i][1] == group[j][1]:
                    same_x[c[1]] += 1
    print("same-token same-cell by xbin (top):", same_x.most_common(10))
    # per-token profile: xbin histogram of pins per token
    prof = defaultdict(Counter)
    for p, tk in zip(pins, toks):
        prof[tk][p["x0"] // 30] += 1
    for tk in ("الله", "رب", "ربك", "لله"):
        print(tk, sorted(prof[tk].items())[:6], "..." if len(prof[tk]) > 6
              else "")


if __name__ == "__main__":
    main()
