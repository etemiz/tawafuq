"""Exact column-maximizing fixed-site selection, without semantic word claims.

Inference receives only geometry and a page count. The exact-PMF artifact is
an independent evaluation oracle, never used to construct the selected sites.
"""
import argparse
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path

import numpy as np

from alignment import ScoreSpec, encode, reference_flags, batch_flags, score_flags
from real_stats import input_manifest
from reference_controls import prepare

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "data"
PLAN = DATA / "research_constructive_selection_plan_v1.json"
EXACT = DATA / "audit_exact_columns_raw_wordlike.json"
OUTPUT = DATA / "research_constructive_selection_v1.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def maximize_columns(slots, draws, spec=ScoreSpec()):
    """Return a deterministic optimal witness and an explicit work counter.

    In a bin with >=2 lines, any j>=2 up to its capacity can select two
    different-line sites plus j-2 arbitrary others, so every selected site
    has a column partner. No cross-bin column interactions exist.
    """
    slots = np.asarray(slots, dtype=float)
    if (slots.ndim != 2 or slots.shape[1] != 2 or not np.isfinite(slots).all()
            or np.any(slots[:, 0] < 0) or np.any(slots[:, 0] != np.floor(slots[:, 0]))
            or isinstance(draws, bool) or not isinstance(draws, (int, np.integer))
            or not 0 <= draws <= len(slots)):
        raise ValueError("need finite site geometry, nonnegative integer lines and a feasible integer count")
    lines, columns, _ = encode(1, slots, spec)
    groups = []
    for column in sorted(set(columns.tolist())):
        indices = np.flatnonzero(columns == column).tolist()
        other = next((i for i in indices if lines[i] != lines[indices[0]]), None)
        groups.append((indices, other))
    states = {0: 0}
    backtrack = []
    transitions = 0
    for indices, other in groups:
        next_states, pointers = {}, {}
        for used in sorted(states):
            for count in range(min(len(indices), draws-used)+1):
                transitions += 1
                score = states[used]+(count if count >= 2 and other is not None else 0)
                total = used+count
                if total not in next_states or score > next_states[total]:
                    next_states[total] = score
                    pointers[total] = (used, count)
        states = next_states
        backtrack.append(pointers)
    selected, total = [], int(draws)
    for (indices, other), pointers in zip(reversed(groups), reversed(backtrack)):
        used, count = pointers[total]
        if count >= 2 and other is not None:
            anchors = [indices[0], other]
            selected.extend(anchors+[i for i in indices if i not in anchors][:count-2])
        else:
            selected.extend(indices[:count])
        total = used
    return dict(selected_indices=sorted(selected), maximum_column_score=states[int(draws)],
                dp_candidate_transitions=transitions, occupied_column_bins=len(groups))


def scalar_counts(placements, spec):
    flags = reference_flags(placements, spec)
    return dict(column=sum(int(c.sum()) for c, m in flags.values()),
                mirror=sum(int(m.sum()) for c, m in flags.values()),
                overlap=sum(int((c & m).sum()) for c, m in flags.values()),
                aligned=sum(int((c | m).sum()) for c, m in flags.values()))


def maximum_event_probability(page_distributions):
    """Sum reaches its global maximum iff every independent page reaches its own."""
    probability = Fraction(1)
    for row in page_distributions.values():
        counts = list(map(int, row["counts"]))
        denominator = int(row["denominator"])
        if not counts or any(c < 0 for c in counts) or sum(counts) != denominator or denominator <= 0:
            raise AssertionError("invalid exact page distribution")
        maximum = max(i for i, c in enumerate(counts) if c)
        probability *= Fraction(counts[maximum], denominator)
    return probability


def analyze():
    plan = json.loads(PLAN.read_text())
    if plan["version"] != "fixed-geometry-constructive-selection-plan-v1":
        raise AssertionError("unexpected constructive study plan")
    spec = ScoreSpec()
    pages, details = prepare(DATA / "real_boxes_v3", raw_observed=True, size_filter=True, exclude_gold=True)
    exact = json.loads(EXACT.read_text())
    manifest = input_manifest(DATA / "real_boxes_v3")
    if (exact["inputs"] != manifest or exact["score"] != spec.to_dict()
            or exact["reference_preprocessing"] != dict(raw_observed=True, size_filter=True, exclude_gold=True)
            or set(exact["page_distributions"]) != set(map(str, pages))):
        raise AssertionError("constructive study does not match the exact-PMF reference population")
    placements, results = {}, {}
    for page, row in pages.items():
        draws = len(row["reds"])
        constructed = maximize_columns(row["slots"], draws, spec)
        selected = constructed["selected_indices"]
        if len(selected) != draws or len(set(selected)) != draws or any(not 0 <= i < len(row["slots"]) for i in selected):
            raise AssertionError("construction did not preserve distinct site count")
        positions = row["slots"][selected].reshape(-1, 2)
        placements[page] = positions
        independent = scalar_counts({page: positions}, spec)["column"]
        distribution = exact["page_distributions"][str(page)]
        counts = list(map(int, distribution["counts"]))
        if int(distribution["denominator"]) != math.comb(len(row["slots"]), draws):
            raise AssertionError("exact-PMF site count differs")
        maximum = max(i for i, c in enumerate(counts) if c)
        if independent != constructed["maximum_column_score"] or independent != maximum:
            raise AssertionError("constructed optimum disagrees with independent score or exact support")
        results[str(page)] = dict(reference_sites=len(row["slots"]), selected_components=draws,
            selected_positions=positions.tolist(), **constructed)
    observed = scalar_counts({page: row["reds"] for page, row in pages.items()}, spec)
    constructed_counts = scalar_counts(placements, spec)
    if observed["column"] != exact["observed"]:
        raise AssertionError("observed exact-model column score differs")
    for selected, scored in ((placements, constructed_counts),
                            ({page: row["reds"] for page, row in pages.items()}, observed)):
        batched = score_flags(batch_flags({page: pos[None, ...] for page, pos in selected.items()}, spec))
        if {k: int(v[0]) for k, v in batched.items()} != scored:
            raise AssertionError("scalar and occupancy witness scoring disagree")
    probability = maximum_event_probability(exact["page_distributions"])
    sources = [PLAN, EXACT, Path(__file__), *(ROOT / "tools" / name for name in
               ("alignment.py", "reference_controls.py", "real_stats.py", "exact_column.py"))]
    return dict(version="fixed-geometry-constructive-selection-v1", plan_sha256=digest(PLAN), score=spec.to_dict(),
        inputs=manifest, source_sha256={p.name: digest(p) for p in sources}, reference_details=details,
        summary=dict(pages=len(pages), reference_sites=sum(len(row["slots"]) for row in pages.values()),
            selected_components=sum(len(row["reds"]) for row in pages.values()), observed=observed,
            constructed=constructed_counts,
            dp_candidate_transitions=sum(row["dp_candidate_transitions"] for row in results.values()),
            pages_all_selected_column_aligned=sum(row["maximum_column_score"] == row["selected_components"] for row in results.values()),
            pages_with_unaligned_selected_components=[int(page) for page, row in results.items()
                if row["maximum_column_score"] != row["selected_components"]]),
        pages=results,
        uniform_null_probability_of_global_maximum=dict(numerator_hex=hex(probability.numerator),
            denominator_hex=hex(probability.denominator),
            event="The total column score equals the sum of individual page maximum column scores.",
            model="Independent uniform k-subsets of the same fixed eligible raw component sites on each page."),
        interpretation="A deterministic optimal witness and a uniform-null probability for the same fixed-geometry component-selection task. No observed red-site indices enter the constructor; k and geometry are supplied. Mirror/union are measured outcomes, not the optimized objective. DP candidate transitions count candidate updates only, not total runtime or human effort. This does not preserve lexical/color identity, within-line red counts or exact morphology, compose text, or model the historical production process. No probability of divine origin, naturalism or human/AI composition follows.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = analyze()
    if args.verify:
        if report != json.loads(OUTPUT.read_text()):
            raise AssertionError("constructive selection study differs")
        print("PASS every constructive witness, exact support maximum, counts and probability")
    else:
        OUTPUT.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report["summary"], indent=2))
    probability = report["uniform_null_probability_of_global_maximum"]
    print("uniform-null global-maximum probability log10 (display only)",
          math.log10(int(probability["numerator_hex"], 16))-math.log10(int(probability["denominator_hex"], 16)))


if __name__ == "__main__":
    main()
