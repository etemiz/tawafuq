"""Stratified raw-component color-label controls, not linguistic word models.

Keep page counts within fixed width/height bins, optionally line and geometric
edge role. Each stratum is sampled independently without replacement. The
observed red sites belong to exactly the reference population. Conditioning
on geometry can freeze labels; report that loss of randomization explicitly.
"""
import argparse
import hashlib
import json
import math
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from alignment import ScoreSpec, batch_flags, eligible_pair, encode, reference_flags, score_flags
from audit_stats import tail_summary
from real_stats import input_manifest, observed_counts
from reference_controls import word_sized
from slot_expectation import avoid, column_hoeffding

DATA = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class Conditioning:
    width_bin: int = 20
    height_bin: int = 10
    line: bool = False
    edge: bool = False
    edge_distance: int = 60

    def __post_init__(self):
        if any(not isinstance(x, int) or x <= 0 for x in
               (self.width_bin, self.height_bin, self.edge_distance)):
            raise ValueError("positive integer geometry bin widths/distances required")


CASES = {
    "page_size": Conditioning(),
    "line_size": Conditioning(line=True),
    "page_size_edge": Conditioning(edge=True),
    "line_size_edge": Conditioning(line=True, edge=True),
    "page_fine_size": Conditioning(width_bin=10, height_bin=5),
}


def stratify(sites, conditioning):
    """Return disjoint index/count groups; inclusive boxes, zero-anchored bins.

    Edge role is a two-bit mask: box within 60px of the left/right extreme
    of its line's size-filtered non-gold raw sites. This is geometric, not
    an independently annotated word/verse boundary.
    """
    extents = {}
    for s in sites:
        lo, hi = extents.get(s["line"], (s["x0"], s["x1"]))
        extents[s["line"]] = min(lo, s["x0"]), max(hi, s["x1"])
    groups = defaultdict(list)
    for i, s in enumerate(sites):
        key = [(s["x1"] - s["x0"] + 1) // conditioning.width_bin,
               (s["y1"] - s["y0"] + 1) // conditioning.height_bin]
        if conditioning.line:
            key.append(s["line"])
        if conditioning.edge:
            lo, hi = extents[s["line"]]
            key.append(int(s["x0"] - lo <= conditioning.edge_distance)
                       + 2 * int(hi - s["x1"] <= conditioning.edge_distance))
        groups[tuple(key)].append(i)
    return [(np.array(indices, dtype=np.int64),
             sum(sites[i]["color"] == "red" for i in indices))
            for _, indices in sorted(groups.items())]


def prepare(data, conditioning):
    pages, excluded = {}, {}
    diagnostics = Counter()
    log10_assignments = 0.0
    for n in range(1, 605):
        path = data / f"page_{n:03d}.json"
        if not path.exists():
            excluded[str(n)] = "missing page artifact"
            continue
        d = json.loads(path.read_text())
        if d["grid"] is None:
            excluded[str(n)] = "no line grid"
            continue
        sites = [s for s in d["slots"] if s["line"] is not None
                 and s["color"] != "gold" and word_sized(s)]
        if len(sites) < 30:
            excluded[str(n)] = "insufficient matched reference sites"
            continue
        positions = np.array([(s["line"], s["cx"]) for s in sites], dtype=float)
        groups = stratify(sites, conditioning)
        reds = positions[[i for i, s in enumerate(sites) if s["color"] == "red"]]
        pages[n] = dict(reds=reds, slots=positions, groups=groups)
        for indices, k in groups:
            size = len(indices)
            diagnostics["strata"] += 1
            diagnostics["reference_sites"] += size
            diagnostics["selected_components"] += k
            if k == size:
                diagnostics["fixed_selected_components"] += k
            elif k:
                diagnostics["randomizable_selected_components"] += k
                diagnostics["mixed_strata"] += 1
                diagnostics["mixed_reference_sites"] += size
            log10_assignments += math.log10(math.comb(size, k))
    if not pages:
        raise ValueError("no eligible comparison pool")
    # Include zero-valued keys for fully deterministic cases as well.
    for key in ("fixed_selected_components", "randomizable_selected_components",
                "mixed_strata", "mixed_reference_sites"):
        diagnostics[key] += 0
    return pages, dict(excluded_pages=excluded, **diagnostics,
                       log10_label_assignments=log10_assignments)


def sample_placements(pages, rng, batch):
    placements = {}
    for n, d in pages.items():
        drawn = np.empty((batch, len(d["reds"]), 2), dtype=float)
        offset = 0
        for indices, k in d["groups"]:
            if not k:
                continue
            if k == len(indices):
                pick = np.broadcast_to(indices, (batch, k))
            else:
                ranks = rng.random((batch, len(indices)))
                pick = indices[np.argpartition(ranks, k - 1, axis=1)[:, :k]]
            drawn[:, offset:offset + k] = d["slots"][pick]
            offset += k
        if offset != len(d["reds"]):
            raise ValueError("stratum counts differ from selected count")
        placements[n] = drawn
    return placements


def simulate(pages, reps, seed=3, batch_size=128, score=ScoreSpec()):
    if reps < 2 or batch_size < 1:
        raise ValueError("reps >= 2 and batch_size >= 1 required")
    rng = np.random.default_rng(seed)
    out = {key: [] for key in ("column", "mirror", "overlap", "aligned")}
    for start in range(0, reps, batch_size):
        placements = sample_placements(pages, rng, min(batch_size, reps - start))
        for key, values in score_flags(batch_flags(placements, score)).items():
            out[key].extend(values.tolist())
    return out


def expectation(pages, score=ScoreSpec()):
    """Hypergeometric first moments for arbitrary independent site strata.

    Conditional on a given site's inclusion, its own stratum has S-1 sites
    and k-1 remaining draws. Other strata are unchanged. Avoid every potential
    other-line column partner and every eligible neighbor mirror partner.
    These two avoidance events involve different pages and hence factor.
    """
    encoded = {}
    for n, d in pages.items():
        lines, cols, mirrors = encode(n, d["slots"], score)
        group_of = np.empty(len(lines), dtype=int)
        sizes, draws = [], []
        columns, cells = defaultdict(Counter), defaultdict(Counter)
        for g, (indices, k) in enumerate(d["groups"]):
            group_of[indices] = g
            sizes.append(len(indices))
            draws.append(k)
            for i in indices:
                columns[int(cols[i])][g, int(lines[i])] += 1
                cells[int(lines[i]), int(mirrors[i])][g] += 1
        encoded[n] = lines, cols, mirrors, group_of, sizes, draws, columns, cells
    totals = dict(column=0.0, mirror=0.0, overlap=0.0, aligned=0.0)
    for n, (lines, cols, mirrors, groups, sizes, draws, columns, _) in encoded.items():
        for li, cb, mb, own in zip(lines, cols, mirrors, groups):
            if not draws[own]:
                continue
            hits = Counter()
            for (g, other_line), count in columns[int(cb)].items():
                if other_line != li:
                    hits[g] += count
            no_col = math.prod(avoid(sizes[g] - int(g == own), count,
                                     draws[g] - int(g == own))
                               for g, count in hits.items())
            no_mirror = 1.0
            for q in (n - 1, n + 1):
                if q not in encoded or not eligible_pair(min(n, q), max(n, q), score):
                    continue
                qdata = encoded[q]
                for g, count in qdata[7].get((int(li), int(mb)), {}).items():
                    no_mirror *= avoid(qdata[4][g], count, qdata[5][g])
            inclusion = draws[own] / sizes[own]
            totals["column"] += inclusion * (1 - no_col)
            totals["mirror"] += inclusion * (1 - no_mirror)
            totals["overlap"] += inclusion * (1 - no_col) * (1 - no_mirror)
            totals["aligned"] += inclusion * (1 - no_col * no_mirror)
    return totals


def verify_report(path, full=False):
    saved = json.loads(path.read_text())
    data = DATA / saved["data_directory"]
    if input_manifest(data) != saved["inputs"]:
        raise AssertionError("geometry-control input hashes differ")
    score = ScoreSpec(**saved["score"])
    for name, row in saved["cases"].items():
        pages, details = prepare(data, Conditioning(**row["conditioning"]))
        stored_details = dict(row["diagnostics"])
        np.testing.assert_allclose(details.pop("log10_label_assignments"),
                                   stored_details.pop("log10_label_assignments"), atol=1e-9)
        if details != stored_details:
            raise AssertionError("geometry-control population/strata differ")
        ref = reference_flags({n: d["reds"] for n, d in pages.items()}, score)
        obs = {key: int(v[0]) for key, v in score_flags(
            {n: (c[None], m[None]) for n, (c, m) in ref.items()}).items()}
        if obs != row["observed"] or len(pages) != row["pages"]:
            raise AssertionError("geometry-control independent observation differs")
        means = expectation(pages, score)
        for key in means:
            np.testing.assert_allclose(means[key], row["analytic_expectation"][key], atol=1e-9)
            summary = tail_summary(obs[key], row["null_samples"][key])
            for field, value in summary.items():
                if value is None or isinstance(value, str):
                    if value != row["results"][key][field]:
                        raise AssertionError("geometry-control MC arithmetic differs")
                else:
                    np.testing.assert_allclose(value, row["results"][key][field])
            if abs(summary["null_mean"] - means[key]) > 8 * summary["null_mean_mc_se"] + 1e-8:
                raise AssertionError("geometry-control MC mean inconsistent with analytic mean")
        bound = column_hoeffding(obs["column"], means["column"], pages)
        np.testing.assert_allclose(bound["log10_upper_bound"],
                                   row["column_hoeffding"]["log10_upper_bound"])
        if full:
            replay = simulate(pages, saved["reps"], saved["seed"], saved["batch_size"], score)
            if replay != row["null_samples"]:
                raise AssertionError("geometry-control deterministic replay differs")
        print(f"PASS geometry control {name}: scalar scores, strata, analytic means, MC arithmetic"
              + (", full replay" if full else ""), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reps", type=int, nargs="?", default=5000)
    parser.add_argument("--data", type=Path, default=DATA / "real_boxes_v3")
    parser.add_argument("--output", type=Path, default=DATA / "audit_geometry_controls.json")
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--full", action="store_true", help="replay simulations during verification")
    args = parser.parse_args()
    if args.verify:
        verify_report(args.verify, args.full)
        return
    if args.reps < 2:
        parser.error("reps >= 2 required")
    started = time.perf_counter()
    score = ScoreSpec()
    cases = {}
    for name, conditioning in CASES.items():
        pages, details = prepare(args.data, conditioning)
        obs = observed_counts(pages, score)
        means = expectation(pages, score)
        samples = simulate(pages, args.reps, score=score)
        cases[name] = dict(conditioning=asdict(conditioning), pages=len(pages),
                           diagnostics=details, observed=obs, analytic_expectation=means,
                           column_hoeffding=column_hoeffding(obs["column"], means["column"], pages),
                           results={k: tail_summary(obs[k], v) for k, v in samples.items()},
                           null_samples=samples)
        print(name, "observed", obs["aligned"], "expected", means["aligned"],
              "fixed", details["fixed_selected_components"], "of", details["selected_components"], flush=True)
    report = dict(version="geometry-stratified-raw-labels-v1", score=score.to_dict(),
                  reps=args.reps, seed=3, batch_size=128, cases=cases,
                  inputs=input_manifest(args.data), data_directory=args.data.name,
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  elapsed_seconds=time.perf_counter() - started,
                  caveat="Exploratory dependent geometry controls, not word/semantic/causal models. "
                  "Coarse geometry bins do not fix morphology. Edge role uses filtered component "
                  "extrema, not certified word or verse boundaries. Frozen labels reduce power.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=1) + "\n")


if __name__ == "__main__":
    main()
