"""CPU controls for observed/reference unit comparability.

The original baseline merges observed red groups but samples raw reference
components. Here identical size filters are applied to both pools, gold
markers can be excluded, and raw-red observations can be a literal subset
of the SAME raw reference sites. These still do not supply linguistic word
boundaries, morphology/width exchangeability, or a human-construction model.
"""
import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np

from alignment import ScoreSpec
from audit_stats import tail_summary
from real_stats import input_manifest, observed_counts, simulate
from slot_expectation import expectation, column_hoeffding

DATA = Path(__file__).resolve().parent / "data"


def word_sized(r):
    w, h = r["x1"] - r["x0"] + 1, r["y1"] - r["y0"] + 1
    return 30 <= w <= 300 and 20 <= h <= 120


def prepare(data, raw_observed=False, size_filter=False, exclude_gold=False):
    pages, excluded = {}, {}
    widths_obs, widths_ref = [], []
    subset = True
    for n in range(1, 605):
        f = data / f"page_{n:03d}.json"
        if not f.exists():
            excluded[str(n)] = "missing page artifact"
            continue
        d = json.loads(f.read_text())
        if d["grid"] is None:
            excluded[str(n)] = "no line grid"
            continue
        slots = [s for s in d["slots"] if s["line"] is not None
                 and (not size_filter or word_sized(s))
                 and (not exclude_gold or s["color"] != "gold")]
        reds = ([s for s in slots if s["color"] == "red"] if raw_observed else
                [r for r in d["reds"] if r["line"] is not None
                 and (not size_filter or word_sized(r))])
        if len(slots) < 30 or len(reds) > len(slots):
            excluded[str(n)] = "insufficient matched reference sites"
            continue
        rpos = [(r["line"], r["cx"]) for r in reds]
        spos = [(s["line"], s["cx"]) for s in slots]
        subset &= not bool(Counter(rpos) - Counter(spos))
        pages[n] = dict(nlines=d["grid"]["n_bands"],
                        reds=np.array(rpos, dtype=float).reshape(-1, 2),
                        slots=np.array(spos, dtype=float).reshape(-1, 2))
        widths_obs.extend(r["x1"] - r["x0"] + 1 for r in reds)
        widths_ref.extend(s["x1"] - s["x0"] + 1 for s in slots)
    if not pages or not widths_obs:
        raise ValueError("no eligible comparison pool")
    if raw_observed and not subset:
        raise AssertionError("raw observed components must be an actual reference subset")
    return pages, dict(excluded_pages=excluded,
                       observed_positions_are_reference_subset=bool(subset),
                       observed_width_quantiles=np.percentile(widths_obs, [10, 50, 90]).tolist(),
                       reference_width_quantiles=np.percentile(widths_ref, [10, 50, 90]).tolist())


def analyze(data, reps=5000, seed=3, batch_size=128):
    specs = [
        ("merged_word_sized_no_gold", False, True, True, "page"),
        ("raw_all_permutation", True, False, False, "page"),
        ("raw_word_sized_no_gold", True, True, True, "page"),
        ("raw_word_sized_no_gold_line", True, True, True, "line"),
    ]
    report = {}
    score = ScoreSpec()
    for name, raw, sizes, no_gold, null in specs:
        pages, details = prepare(data, raw, sizes, no_gold)
        observed = observed_counts(pages, score)
        samples = simulate(pages, reps, seed, batch_size, score, null)
        means, _ = expectation(pages, score, null)
        total = sum(len(p["reds"]) for p in pages.values())
        report[name] = dict(raw_observations=raw, word_size_filter=sizes,
                            exclude_gold=no_gold, null_model=null, score=score.to_dict(),
                            pages=len(pages), total_components=total,
                            observed=observed, observed_rate=observed["aligned"] / total,
                            analytic_expectation=means,
                            results={k: tail_summary(observed[k], v) for k, v in samples.items()},
                            column_hoeffding=column_hoeffding(observed["column"], means["column"], pages),
                            null_samples=samples, **details)
        print(name, "n", total, "observed", observed["aligned"] / total,
              "reference mean", np.mean(samples["aligned"]) / total,
              "column Hoeffding log10", report[name]["column_hoeffding"]["log10_upper_bound"], flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reps", type=int, nargs="?", default=5000)
    parser.add_argument("--data", type=Path, default=DATA / "real_boxes_v3")
    parser.add_argument("--output", type=Path, default=DATA / "audit_reference_controls.json")
    args = parser.parse_args()
    started = time.perf_counter()
    cases = analyze(args.data, args.reps)
    report = dict(version="unit-comparability-controls-v1", cases=cases, seed=3,
                  batch_size=128, inputs=input_manifest(args.data), data_directory=args.data.name,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  elapsed_seconds=time.perf_counter() - started,
                  caveat="Exploratory component controls, not complete linguistic word models. "
                  "Literal raw-site permutation assumes color-label exchangeability conditional "
                  "on fixed sites/counts; glyph/morphology/width dependencies still require modeling.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
