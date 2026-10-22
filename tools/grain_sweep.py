"""Audited cross-page identity grain sweep on committed semantic pins.

Unlike the historical sweep, preserves page identity, does not collapse
fine rows/columns into fixed 15x32 tails, and tests genuine mirrored pairs.
Columns partition [0,1024] into ceil(1024/requested_width) equal bins so
opposite cells have an exact reflection rule. Actual widths are recorded.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np

from word_pair_census import load_pins, pin_manifest
from pair_statistics import word_cell_pairs
from audit_stats import tail_summary

DATA = Path(__file__).resolve().parent / "data"


def make_cells(pins, rowpx=112.0, colpx=30.0):
    nb = math.ceil(1024 / colpx) if colpx is not None else 1
    cells = []
    for p in pins:
        row = math.floor(p["yc"] / rowpx) if rowpx is not None else 0
        col = min(nb - 1, max(0, math.floor(p["xc"] / (1024 / nb))))
        cells.append((p["page"], row, col))
    return cells, nb


def analyze(pins, reps, seed=53):
    rng = np.random.default_rng(seed)
    grains = [("r112_x30", 112, 30), ("r112_x15", 112, 15),
              ("r112_x60", 112, 60), ("r56_x30", 56, 30),
              ("r224_x30", 224, 30), ("row_only", 112, None),
              ("col_only", None, 30)]
    report = {}
    for name, rowpx, colpx in grains:
        for kind in ("mag", "cri"):
            sub = [p for p in pins if p["kind"] == kind]
            cells, nb = make_cells(sub, rowpx, colpx)
            words = [p["word"] for p in sub]
            items = [(w, *cell) for w, cell in zip(words, cells)]
            modes = (False, True) if colpx is not None else (False,)
            observed = {m: word_cell_pairs(items, nb if m else None) for m in modes}
            samples = {m: [] for m in modes}
            for _ in range(reps):
                perm = rng.permutation(len(words))
                sim = [(words[i], *cell) for i, cell in zip(perm, cells)]
                for m in modes:
                    samples[m].append(word_cell_pairs(sim, nb if m else None))
            for m in modes:
                key = f"{name}{'_mirror' if m else ''}:{kind}"
                report[key] = dict(n=len(sub), n_columns=nb,
                                   actual_column_width=1024 / nb,
                                   row_width=rowpx, mirror=m,
                                   inference=tail_summary(observed[m], samples[m]),
                                   null_samples=samples[m])
                print(key, "obs", observed[m], "null", np.mean(samples[m]),
                      "tail", report[key]["inference"]["plus_one_mc"], flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reps", type=int, nargs="?", default=1000)
    parser.add_argument("--src", default="mark_identity_semantic.json")
    parser.add_argument("--output", type=Path, default=DATA / "audit_grain_sweep.json")
    args = parser.parse_args()
    if args.reps < 2:
        parser.error("reps >= 2 required")
    pins = load_pins(args.src)
    results = analyze(pins, args.reps)
    report = dict(version="cross-page-grains-v2", src=args.src, seed=53,
                  inputs=pin_manifest(args.src),
                  reps=args.reps, tests=len(results), results=results,
                  caveat="Exploratory multiple-grain sweep, unadjusted individual tails. "
                  "Incomplete selected pins and global label exchangeability limit inference.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
