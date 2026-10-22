"""Audited component alignment and real-slot conditional CPU simulation.

Run: python tools/real_stats.py 10000 --output logs/global-audit.json
The versioned score is not the historical 72.65% statistic. No z-to-p tails.
"""
import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np

from alignment import (ScoreSpec, batch_flags, encode, sample_placements,
                       score_flags)
from audit_stats import tail_summary
from slot_expectation import expectation, column_hoeffding

DATA = Path(__file__).resolve().parent / "data" / "real_boxes"
NB = 32
W = 1024.0


def load_all(first=1, last=604, include_empty=False, data=DATA):
    """Keep the legacy default empty-page exclusion for importing old tools.

    Audited commands explicitly include valid empty pages. Store source box
    indices so cropped features can never silently shift ordinal identity.
    """
    pages = {}
    for n in range(first, last + 1):
        f = data / f"page_{n:03d}.json"
        if not f.exists():
            continue
        d = json.loads(f.read_text())
        if d["grid"] is None:
            continue
        inds = [i for i, r in enumerate(d["reds"]) if r["line"] is not None]
        reds = [(d["reds"][i]["line"], d["reds"][i]["cx"]) for i in inds]
        slots = [(s["line"], s["cx"]) for s in d["slots"] if s["line"] is not None]
        if (not reds and not include_empty) or len(slots) < 30:
            continue
        nl = d["grid"]["n_bands"]
        for label, positions in (("reds", reds), ("slots", slots)):
            if any(not (0 <= line < nl) or int(line) != line or not np.isfinite(x)
                   for line, x in positions):
                raise ValueError(f"invalid {label} on page {n}")
        if len(reds) > len(slots):
            raise ValueError(f"page {n}: fewer slots than colored components")
        pages[n] = dict(nlines=nl, reds=np.array(reds, dtype=np.float64).reshape(-1, 2),
                        slots=np.array(slots, dtype=np.float64).reshape(-1, 2),
                        red_indices=inds)
    if not pages:
        raise ValueError("no eligible pages")
    return pages


def prep_slot_cloud(slots, nlines):
    """Compatibility interface for older census scripts (not their validation)."""
    lines, cols, _ = encode(1, slots, ScoreSpec())
    return lines, cols, slots[:, 1]


def input_manifest(data=DATA):
    return {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(data.glob("page_*.json"))}


def observed_counts(pages, spec):
    placements = {n: d["reds"][None, ...] for n, d in pages.items()}
    return {k: int(v[0]) for k, v in score_flags(batch_flags(placements, spec)).items()}


def simulate(pages, reps, seed=3, batch_size=128, spec=ScoreSpec(), null_model="page"):
    if reps < 2 or batch_size < 1:
        raise ValueError("reps >= 2 and batch_size >= 1 required")
    rng = np.random.default_rng(seed)
    out = {k: [] for k in ("column", "mirror", "overlap", "aligned")}
    for start in range(0, reps, batch_size):
        b = min(batch_size, reps - start)
        counts = score_flags(batch_flags(sample_placements(pages, rng, b, null_model), spec))
        for k, v in counts.items():
            out[k].extend(v.tolist())
    return out


def run(pages, placement, reps=1, seed=3):
    """Legacy return shape with corrected scoring.

    The third result is a histogram of MAXIMUM BIN COMPONENT OCCUPANCY,
    not a guarantee that all occupants lie on different text lines.
    """
    if placement not in ("observed", "null") or reps < 1:
        raise ValueError("placement must be observed/null and reps >= 1")
    spec = ScoreSpec()
    count = 1 if placement == "observed" else reps
    aligned = np.zeros(count, dtype=np.int64)
    curves = np.zeros((count, 20), dtype=np.int64)
    rng = np.random.default_rng(seed)
    for start in range(0, count, 128):
        b = min(128, count - start)
        positions = ({n: d["reds"][None] for n, d in pages.items()}
                     if placement == "observed" else sample_placements(pages, rng, b))
        aligned[start:start + b] = score_flags(batch_flags(positions, spec))["aligned"]
        for n, p in positions.items():
            _, cols, _ = encode(n, p, spec)
            offsets = np.arange(b)[:, None] * spec.bins
            best = np.bincount((cols + offsets).ravel(), minlength=b * spec.bins).reshape(b, spec.bins).max(axis=1)
            curves[np.arange(start, start + b), np.minimum(best, 19)] += 1
    return np.full(count, sum(len(d["reds"]) for d in pages.values())), aligned, curves


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reps", type=int, nargs="?", default=1000)
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--pairing", choices=("adjacent", "facing", "leaf", "none"), default="adjacent")
    parser.add_argument("--column-origin", type=float, default=26.0)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--data", type=Path, default=DATA.parent / "real_boxes_v3",
                        help="component artifact directory; audited v3 extraction by default")
    parser.add_argument("--null-model", choices=("page", "line"), default="page")
    args = parser.parse_args()
    start = time.perf_counter()
    pages = load_all(include_empty=True, data=args.data)
    spec = ScoreSpec(pairing=args.pairing, column_origin=args.column_origin)
    obs = observed_counts(pages, spec)
    total = sum(len(d["reds"]) for d in pages.values())
    samples = simulate(pages, args.reps, args.seed, args.batch_size, spec, args.null_model)
    analytic, _ = expectation(pages, spec, args.null_model)
    report = dict(score=spec.to_dict(), seed=args.seed, batch_size=args.batch_size,
                  pages=len(pages), total_components=total,
                  excluded_pages=sorted(set(range(1, 605)) - pages.keys()),
                  observed=obs, observed_rate=obs["aligned"] / total,
                  analytic_expectation=analytic,
                  column_hoeffding=column_hoeffding(obs["column"], analytic["column"], pages),
                  results={k: tail_summary(obs[k], v) for k, v in samples.items()},
                  null_samples=samples, inputs=input_manifest(args.data),
                  data_directory=args.data.name,
                  null_model=args.null_model,
                  numpy=np.__version__, python=platform.python_version(),
                  elapsed_seconds=time.perf_counter() - start)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    brief = {k: v for k, v in report.items() if k not in ("null_samples", "inputs")}
    print(json.dumps(brief, indent=2))


if __name__ == "__main__":
    main()
