"""Phrase-mirror pair test (A2a, S16): do semantically PAIRED words land
at same or x-mirrored layout cells across pages?

The tawafuq claim, generic form: Hayrat colors word A (e.g. الجنه) in a
verse on page p1 and its semantic partner B (e.g. النار) on another page
at the SAME cell, or at an opposite cell of a symmetric nominal page
partition, as a designed visual pairing.

Uses semantic-mode identity hypotheses. Many literature pair words have
no pins in this selected set; that does not establish absence of colored
occurrences. The testable pinned pairs are:
  P1 janna_nar  (الجنه vs النار)
  P2 allah_rb   (الله vs رب-family, crimson)
  P3 allah_huwa (الله vs هو tint, la_ilaha_illa_huwa echo)
  P4 refrain    (فباي+ءالاء+ربكما vs تكذبان)

Nulls:
  slot      — same page counts, cells replaced by random page slots
              (layout chance), pair assignment kept.
  pair_perm — cells kept, A/B labels flipped at random within the pair
              (pair-specificity given the observed cell cloud).
  word_rand — cells kept, A/B labels drawn from the pair pool's marginal
              frequencies, with variable label counts (diagnostic).

Usage: python tools/phrase_mirror_test.py [REPS] [--all]
"""
import json
import argparse
import sys
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from word_pair_census import load_pins, load_slots, pin_boxes, pin_manifest, NBINS, ROW
from grain_sweep import make_cells
from audit_stats import tail_summary

DATA = Path(__file__).resolve().parent / "data"

PAIRS = {
    "janna_nar": ({"الجنه"}, {"النار"}),
    "allah_rb": ({"الله"}, {"رب", "ربي", "ربك", "ربكم", "ربهم", "ربنا", "ربه", "ربكما"}),
    "allah_huwa": ({"الله"}, {"هو"}),
    "refrain": ({"فباي", "ءالاء", "ربكما"}, {"تكذبان"}),
}


def mirror_xb(xb):
    return NBINS - 1 - xb


def pair_stats(items, bins=None):
    """items: list of (page, yb, xb, side). side in {0,1} = which word of
    the pair. Returns (same, mirror, facing_same, facing_mirror)."""
    nb = NBINS if bins is None else bins
    counts = Counter((y, x, side) for p, y, x, side in items)
    pages = Counter(items)
    same = sum(n * counts[(y, x, 1)] for (y, x, side), n in counts.items() if side == 0)
    same -= sum(n * pages[(p, y, x, 1)] for (p, y, x, side), n in pages.items() if side == 0)
    mirror = sum(n * counts[(y, nb - 1 - x, 1)]
                 for (y, x, side), n in counts.items() if side == 0)
    mirror -= sum(n * pages[(p, y, nb - 1 - x, 1)]
                  for (p, y, x, side), n in pages.items() if side == 0)
    # Each physical spread counted once, from its even page to odd neighbor.
    fs = sum(n * pages[(p + 1, y, x, 1 - side)]
             for (p, y, x, side), n in pages.items() if p % 2 == 0)
    fm = sum(n * pages[(p + 1, y, nb - 1 - x, 1 - side)]
             for (p, y, x, side), n in pages.items() if p % 2 == 0)
    return same, mirror, fs, fm


def main():
    global NBINS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reps", type=int, nargs="?", default=1000)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--src")
    parser.add_argument("--output", type=Path, default=DATA / "audit_phrase_mirror.json")
    args = parser.parse_args()
    reps = args.reps
    if reps < 2:
        parser.error("reps >= 2 required")
    src = args.src or ("mark_identity.json" if args.all else "mark_identity_semantic.json")
    pins = load_pins(src)
    cells, NBINS = make_cells(pins, 112, 30)
    for p, (_, yb, xb) in zip(pins, cells):
        p["yb"], p["xb"] = yb, xb
    slots = load_slots(pin_boxes(src))
    rng = np.random.default_rng(23)
    report = {"source": src, "reps": reps, "pairs": {}}
    for name, (wa, wb) in PAIRS.items():
        a = [p for p in pins if p["word"] in wa]
        b = [p for p in pins if p["word"] in wb]
        items = ([(p["page"], p["yb"], p["xb"], 0) for p in a]
                 + [(p["page"], p["yb"], p["xb"], 1) for p in b])
        obs = pair_stats(items)
        # --- nulls ---
        ns_s, ns_m, pp_s, pp_m, wr_s, wr_m = [], [], [], [], [], []
        page_count = Counter(p["page"] for p in a + b)
        counts_a = Counter(p["page"] for p in a)
        counts_b = Counter(p["page"] for p in b)
        # slot null: replace cells with random slots, keep sides
        for _ in range(reps):
            sim = []
            for pg in page_count:
                sl = slots.get(pg)
                cnt_a = counts_a[pg]
                cnt_b = counts_b[pg]
                k = cnt_a + cnt_b
                if sl is None or len(sl) < k:
                    raise ValueError(f"page {pg}: missing/insufficient slots")
                pick = rng.choice(len(sl), size=k, replace=False)
                for t, (cy, cx) in zip(range(k), sl[pick]):
                    yb = int(cy // ROW)
                    xb = min(NBINS - 1, max(0, int(cx / (1024 / NBINS))))
                    side = 0 if t < cnt_a else 1
                    sim.append((pg, yb, xb, side))
            s, m, _, _ = pair_stats(sim)
            ns_s.append(s)
            ns_m.append(m)
        ns_s = np.array(ns_s)
        ns_m = np.array(ns_m)
        # pair-perm + word-rand nulls: keep cells, shuffle labels
        cells = [(p["page"], p["yb"], p["xb"]) for p in a + b]
        words_pair = ([p["word"] for p in a] + [p["word"] for p in b])
        for _ in range(reps):
            # pair_perm: shuffle the side assignment among the pair pins
            perm = rng.permutation(len(a) + len(b))
            sides = [0] * len(a) + [1] * len(b)
            sim = [(*cells[perm[i]], sides[i]) for i in range(len(cells))]
            s, m, _, _ = pair_stats(sim)
            pp_s.append(s)
            pp_m.append(m)
            # word_rand: draw random words FROM THE PAIR'S OWN PIN POOL at
            # the same cells (no drop artifact; tests whether THIS split
            # of the pool matters vs any random word split)
            draw = rng.integers(0, len(words_pair), size=len(cells))
            sim2 = []
            for (pg, yb, xb), wi in zip(cells, draw):
                w = words_pair[wi]
                side = 0 if w in wa else 1
                sim2.append((pg, yb, xb, side))
            s, m, _, _ = pair_stats(sim2)
            wr_s.append(s)
            wr_m.append(m)
        pp_s = np.array(pp_s)
        pp_m = np.array(pp_m)
        wr_s = np.array(wr_s)
        wr_m = np.array(wr_m)
        row = dict(
            status="untestable_missing_side" if not a or not b else "conditional_selected_pins",
            null_samples=dict(slot_same=ns_s.tolist(), slot_mirror=ns_m.tolist(),
                              pairperm_same=pp_s.tolist(), pairperm_mirror=pp_m.tolist(),
                              wordrand_same=wr_s.tolist(), wordrand_mirror=wr_m.tolist()),
            slot_same_inference=tail_summary(obs[0], ns_s),
            slot_mirror_inference=tail_summary(obs[1], ns_m),
            pairperm_same_inference=tail_summary(obs[0], pp_s),
            pairperm_mirror_inference=tail_summary(obs[1], pp_m),
            n_a=len(a), n_b=len(b),
            obs_same=obs[0], obs_mirror=obs[1],
            obs_facing_same=obs[2], obs_facing_mirror=obs[3],
            slot_same_mu=round(float(ns_s.mean()), 1),
            slot_same_sd=round(float(ns_s.std()), 1),
            slot_same_z=round(float((obs[0] - ns_s.mean()) / ns_s.std()), 1)
            if ns_s.std() else None,
            slot_mirror_mu=round(float(ns_m.mean()), 1),
            slot_mirror_sd=round(float(ns_m.std()), 1),
            slot_mirror_z=round(float((obs[1] - ns_m.mean()) / ns_m.std()), 1)
            if ns_m.std() else None,
            pairperm_same_mu=round(float(pp_s.mean()), 1),
            pairperm_same_sd=round(float(pp_s.std()), 1),
            pairperm_same_z=round(float((obs[0] - pp_s.mean()) / pp_s.std()), 1)
            if pp_s.std() else None,
            pairperm_mirror_mu=round(float(pp_m.mean()), 1),
            pairperm_mirror_sd=round(float(pp_m.std()), 1),
            pairperm_mirror_z=round(float((obs[1] - pp_m.mean()) / pp_m.std()), 1)
            if pp_m.std() else None,
            wordrand_same_mu=round(float(wr_s.mean()), 1),
            wordrand_same_sd=round(float(wr_s.std()), 1),
            wordrand_same_z=round(float((obs[0] - wr_s.mean()) / wr_s.std()), 1)
            if wr_s.std() else None,
            wordrand_mirror_mu=round(float(wr_m.mean()), 1),
            wordrand_mirror_sd=round(float(wr_m.std()), 1),
            wordrand_mirror_z=round(float((obs[1] - wr_m.mean()) / wr_m.std()), 1)
            if wr_m.std() else None)
        report["pairs"][name] = row
        print(f"== {name}: nA={row['n_a']} nB={row['n_b']}")
        print(f"   same:   obs={row['obs_same']} slot {row['slot_same_mu']}±"
              f"{row['slot_same_sd']} z={row['slot_same_z']} | "
              f"pairperm z={row['pairperm_same_z']} | "
              f"wordrand z={row['wordrand_same_z']}")
        print(f"   mirror: obs={row['obs_mirror']} slot {row['slot_mirror_mu']}±"
              f"{row['slot_mirror_sd']} z={row['slot_mirror_z']} | "
              f"pairperm z={row['pairperm_mirror_z']} | "
              f"wordrand z={row['wordrand_mirror_z']}")
        print(f"   facing: same={row['obs_facing_same']} "
              f"mirror={row['obs_facing_mirror']}")
    report["version"] = "physical-phrase-pairs-v2"
    report["inputs"] = pin_manifest(src)
    report["column_bins"] = NBINS
    report["caveat"] = ("No pins does not mean no colored occurrences. Selected pins, global "
                        "exchangeability and exploratory pair choices limit inference.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(f"saved {args.output}")


if __name__ == "__main__":
    main()
