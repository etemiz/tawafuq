"""Reproduce alignment conditional on archived SHAPE labels, CPU only.

Default scoring is within-type on BOTH observed and reference placements.
--scope pooled instead asks whether members align with ANY colored component.
These are different questions; neither validates the archived semantic labels.
"""
import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np

from alignment import ScoreSpec, batch_flags, sample_placements
from audit_stats import tail_summary
from real_stats import load_all, input_manifest, simulate, observed_counts

DATA = Path(__file__).resolve().parent / "data"


def classify_types():
    """Compatibility API using committed assignments, never temporary pixels."""
    with np.load(DATA / "red_types.npz", allow_pickle=False) as d:
        return d["types"], d["lab"], d["deep"], d["meta"]


def load_type_labels(pages, archive=DATA / "red_types.npz"):
    with np.load(archive, allow_pickle=False) as d:
        types, meta = d["types"], d["meta"]
    if len(types) != len(meta):
        raise ValueError("label/meta length mismatch")
    labels = {n: np.full(len(d["reds"]), "unclassified", dtype="U32")
              for n, d in pages.items()}
    ranks = {n: {i: rank for rank, i in enumerate(d["red_indices"])}
             for n, d in pages.items()}
    seen = set()
    for ty, row in zip(types, meta):
        n, i = map(int, row[:2])
        if n != row[0] or i != row[1] or (n, i) in seen:
            raise ValueError("invalid/duplicate source-box label identity")
        seen.add((n, i))
        if n not in pages:
            continue
        if i not in ranks[n]:
            raise ValueError(f"stale label for excluded box {(n, i)}")
        rank = ranks[n][i]
        if not np.allclose(pages[n]["reds"][rank], [row[3], row[2]], atol=0.01, rtol=0):
            raise ValueError(f"stale label coordinates for {(n, i)}")
        labels[n][rank] = ty
    return labels


def per_word_aligned(pages, order=None):
    flags = batch_flags({n: d["reds"][None, ...] for n, d in pages.items()})
    return {(n, i): bool((col | mir)[0, i])
            for n, (col, mir) in flags.items() for i in range(col.shape[1])}


def type_pages(pages, labels, ty):
    return {n: dict(d, reds=d["reds"][labels[n] == ty]) for n, d in pages.items()}


def pooled_counts(flags, labels, types):
    batch = next(iter(flags.values()))[0].shape[0]
    out = {ty: np.zeros(batch, dtype=np.int64) for ty in types}
    for n, (col, mir) in flags.items():
        combined = col | mir
        for ty in types:
            out[ty] += combined[:, labels[n] == ty].sum(axis=1)
    return out


def analyze(pages, labels, reps, seed=3, batch_size=128, scope="same-type"):
    spec = ScoreSpec()
    types = sorted({str(ty) for v in labels.values() for ty in v})
    totals = Counter(str(ty) for v in labels.values() for ty in v)
    results, samples = {}, {}
    if scope == "pooled":
        obs = pooled_counts(batch_flags({n: d["reds"][None, ...]
                                        for n, d in pages.items()}, spec), labels, types)
        rng = np.random.default_rng(seed)
        samples = {ty: [] for ty in types}
        for start in range(0, reps, batch_size):
            placements = sample_placements(pages, rng, min(batch_size, reps - start))
            count = pooled_counts(batch_flags(placements, spec), labels, types)
            for ty in types:
                samples[ty].extend(count[ty].tolist())
        obs = {ty: int(v[0]) for ty, v in obs.items()}
    elif scope == "same-type":
        obs = {}
        for ty in types:
            sub = type_pages(pages, labels, ty)
            obs[ty] = observed_counts(sub, spec)["aligned"]
            samples[ty] = simulate(sub, reps, seed, batch_size, spec)["aligned"]
    else:
        raise ValueError("unknown scope")
    for ty in types:
        results[ty] = dict(n=totals[ty], observed_aligned=obs[ty],
                           observed_rate=obs[ty] / totals[ty],
                           null_rate=float(np.mean(samples[ty])) / totals[ty],
                           inference=tail_summary(obs[ty], samples[ty]))
    return dict(scope=scope, score=spec.to_dict(), results=results, null_samples=samples,
                caveat="Conditional on archived visual shape assignments; semantic label "
                "accuracy is not established by this calculation. Type tails are dependent.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reps", type=int, nargs="?", default=1000)
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--scope", choices=("same-type", "pooled"), default="same-type")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.reps < 2 or args.batch_size < 1:
        parser.error("reps >= 2 and batch-size >= 1 required")
    start = time.perf_counter()
    pages = load_all(include_empty=True)
    labels = load_type_labels(pages)
    rep = analyze(pages, labels, args.reps, args.seed, args.batch_size, args.scope)
    rep.update(seed=args.seed, batch_size=args.batch_size, inputs=input_manifest(),
               labels_sha256=hashlib.sha256((DATA / "red_types.npz").read_bytes()).hexdigest(),
               elapsed_seconds=time.perf_counter() - start)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rep, indent=2) + "\n")
    for ty, r in rep["results"].items():
        print(f"{ty:14} n={r['n']:4d} observed={r['observed_rate']:.4%} "
              f"null={r['null_rate']:.4%} exceed={r['inference']['exceedances']}/{args.reps}")


if __name__ == "__main__":
    main()
