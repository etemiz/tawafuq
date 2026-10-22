"""Exact occupancy arithmetic for explicit fixed-page component-slot models.

This does not turn source-selected showcase anecdotes into calibrated
corpus-wide p-values. In particular it does not assume independence of
features on one page or of selected pages.
"""
import json
import argparse
import math
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.stats import combine_pvalues

from real_stats import load_all
from alignment import ScoreSpec, encode
from divine_census import TRUE_FORMS

DATA = Path(__file__).resolve().parent / "data"


def max_bin_tail(capacities, draws, threshold):
    """Exact uniform-subset P(max bin occupancy >= threshold), integer DP.

    Product over bins of sum_{j=0}^{threshold-1} C(m_bin,j) z^j,
    coefficient of z^draws counts subsets avoiding the event. No MC,
    floating cancellation, independence assumption, or union approximation.
    """
    capacities = list(map(int, capacities))
    if any(m < 0 for m in capacities) or not 0 <= draws <= sum(capacities):
        raise ValueError("invalid population or sample")
    if threshold <= 0:
        return Fraction(1)
    ways = [0] * (draws + 1)
    ways[0] = 1
    for m in capacities:
        nxt = [0] * (draws + 1)
        for used, value in enumerate(ways):
            if not value:
                continue
            for j in range(min(m, threshold - 1, draws - used) + 1):
                nxt[used + j] += value * math.comb(m, j)
        ways = nxt
    total = math.comb(sum(capacities), draws)
    return Fraction(total - ways[draws], total)


def manual_census(pages):
    manual = json.loads((DATA / "audit_manual_page422.json").read_text())
    rows = manual["labels"]
    page = pages[422]
    bins = encode(422, page["reds"], ScoreSpec())[1]
    for r in rows:
        if not np.allclose(page["reds"][r["index"]], [r["line"], r["cx"]], atol=0.01, rtol=0):
            raise ValueError("manual label/source box association changed")
    best = int(np.bincount(bins).argmax())
    is_name = lambda w: w == "الله" or w in TRUE_FORMS
    return dict(annotation="audit_manual_page422.json", components=len(rows),
                lafzullah_total=sum(is_name(r["word"]) for r in rows),
                best_component_bin=best, best_component_count=int(np.count_nonzero(bins == best)),
                best_bin_lafzullah=int(sum(is_name(r["word"]) and bins[r["index"]] == best for r in rows)),
                other_best_bin_words=[r["word"] for r in rows
                                      if not is_name(r["word"]) and bins[r["index"]] == best],
                verdict="The 12-component column contains 11 lafzullah forms plus Hu. "
                        "The historical 12-of-16 semantic threshold is not reproduced.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA / "real_boxes_v3")
    args = parser.parse_args()
    pages = load_all(include_empty=True, data=args.data)
    report = {"status": "Model arithmetic only; source selection and semantic identities uncalibrated.",
              "fixed_page_422": [], "historical_fisher_arithmetic": {}}
    report["independent_manual_page422"] = manual_census(pages)
    report["component_source"] = args.data.name
    report["legacy_napkin_arithmetic"] = dict(
        explicit_expression="(1/8.5)**(3.4*604)",
        log10_value=-3.4 * 604 * math.log10(8.5),
        verdict="Real-number arithmetic only. Fractional average word counts, event definition, "
                "page independence and a human-construction interpretation are not calibrated.")
    slots = pages[422]["slots"]
    for width in (30, 60, 90):
        nb = ScoreSpec().bins
        bins = np.clip(np.floor((slots[:, 1] - 26) / width), 0, nb - 1).astype(int)
        capacities = np.bincount(bins, minlength=nb)
        for draws in (16, len(pages[422]["reds"])):
            p = max_bin_tail(capacities, draws, 12)
            report["fixed_page_422"].append(dict(
                bin_width=width, draws=draws, threshold=12,
                slot_count=len(slots), capacities=capacities.tolist(),
                exact_numerator=str(p.numerator), exact_denominator=str(p.denominator),
                probability=float(p),
                caveat="Counts component occupancies, not 12 semantic Allah tokens on distinct lines; "
                       "fixed-page conditional model, not selection-adjusted."))
    other = [1.2e-8, 8.5e-9, 7e-7]
    for label, p422 in (("original", 7.3e-14), ("upgraded", 1.4e-17)):
        stat, p = combine_pvalues([p422] + other, method="fisher")
        report["historical_fisher_arithmetic"][label] = dict(
            input_values=[p422] + other, statistic=float(stat),
            independent_uniform_formula=float(p), times_1320=float(p * 1320),
            verdict="Arithmetic reproducible, inference unvalidated: constituent tails, "
                    "independence, source selection and correction family not established.")
    report["invalid_inferences"] = [
        "Alignment flags within a column are dependent, so individual-word binomial tails need independent justification.",
        "A published description predating our scans does not make its subevents independent.",
        "Multiplying marginal subevent probabilities is not the probability chain rule.",
        "330 word types x 4 styles does not enumerate page, tolerance, edition and source selection.",
        "A random-slot probability cannot be used as a skilled scribe's per-page failure probability.",
        "The strict napkin single-column event is not equivalent to any-column-or-mirror alignment.",
        "A 30px fixed bin is not a sliding +/-15px interval; phase and clipping matter.",
    ]
    (DATA / "audit_showcase.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
