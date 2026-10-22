"""Exact page column-score distributions and rational Markov tail bounds.

For each x-bin with m slots split into lines of sizes m_l, selecting j>0
slots has C(m,j) possibilities. A_j=sum_l C(m_l,j) put ALL selected slots
on one line (column score 0); C(m,j)-A_j involve >=2 lines (score j).
Multiply these bivariate polynomials over bins, tracking (draws, score).
Coefficient [z^k y^a] counts subsets with column score a exactly.

For independent pages and any integer b>1, Markov's inequality gives
P(sum X_p >= observed) <= b^-observed * product_p E[b^X_p].
Every coefficient and the final bound here is an exact Python integer or
Fraction. There is no simulated/extrapolated tail or numerical optimizer.
"""
import json
import math
from fractions import Fraction
from pathlib import Path

import numpy as np

from alignment import ScoreSpec, encode

DATA = Path(__file__).resolve().parent / "data"


def column_distribution(slots, draws, spec=ScoreSpec()):
    """Return integer subset counts by aligned score, denominator C(S,k)."""
    if not 0 <= draws <= len(slots):
        raise ValueError("invalid subset size")
    lines, cols, _ = encode(1, slots, spec)
    ways = np.zeros((draws + 1, draws + 1), dtype=object)
    ways[0, 0] = 1
    for col in np.unique(cols):
        selected_lines = lines[cols == col]
        _, counts = np.unique(selected_lines, return_counts=True)
        m = len(selected_lines)
        nxt = ways.copy()  # choose zero from this bin
        for j in range(1, min(m, draws) + 1):
            single = sum(math.comb(int(n), j) for n in counts if n >= j)
            multi = math.comb(m, j) - single
            if single:
                nxt[j:, :] += ways[:-j, :] * single
            if multi:
                nxt[j:, j:] += ways[:-j, :-j] * multi
        ways = nxt
    result = [int(n) for n in ways[draws]]
    denominator = math.comb(len(slots), draws)
    if sum(result) != denominator:
        raise AssertionError("exact subset accounting failed")
    return result, denominator


def markov_bound(distributions, observed, base):
    if not isinstance(base, int) or base <= 1:
        raise ValueError("integer exponential base > 1 required")
    numerator = math.prod(sum(n * base ** score for score, n in enumerate(counts))
                          for counts, denominator in distributions)
    denominator = math.prod(d for c, d in distributions) * base ** observed
    return min(Fraction(1), Fraction(numerator, denominator))


def analyze(pages, observed, spec=ScoreSpec(), bases=(2, 3, 4, 8)):
    by_page = {}
    distributions = []
    mean = Fraction(0)
    for n, d in pages.items():
        counts, denominator = column_distribution(d["slots"], len(d["reds"]), spec)
        distributions.append((counts, denominator))
        mean += Fraction(sum(score * count for score, count in enumerate(counts)), denominator)
        by_page[str(n)] = dict(counts=[str(x) for x in counts], denominator=str(denominator))
    bounds = {}
    for base in bases:
        bound = markov_bound(distributions, observed, base)
        bounds[str(base)] = dict(
            numerator_hex=hex(bound.numerator), denominator_hex=hex(bound.denominator),
            log10_upper_bound=math.log10(bound.numerator) - math.log10(bound.denominator))
    best = min(bounds, key=lambda b: Fraction(int(bounds[b]["numerator_hex"], 16),
                                            int(bounds[b]["denominator_hex"], 16)))
    return dict(version="exact-column-subsets-v1", score=spec.to_dict(),
                observed=observed, analytic_column_mean=float(mean),
                page_distributions=by_page, bounds=bounds, best_base=int(best),
                caveat="Exact rational MODEL-CONDITIONAL upper bounds for the column score. "
                "Not exact tail probabilities, not a human-construction model, not selection-adjusted.")


def main():
    import argparse
    from real_stats import load_all, input_manifest, observed_counts
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA / "real_boxes_v3")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--raw-wordlike", action="store_true",
                        help="literal raw-component subset with common size filter and gold removed")
    args = parser.parse_args()
    if args.raw_wordlike:
        from reference_controls import prepare
        pages, details = prepare(args.data, raw_observed=True, size_filter=True, exclude_gold=True)
    else:
        pages = load_all(include_empty=True, data=args.data)
    spec = ScoreSpec()
    observed = observed_counts(pages, spec)["column"]
    out = analyze(pages, observed, spec)
    out["inputs"] = input_manifest(args.data)
    out["data_directory"] = args.data.name
    if args.raw_wordlike:
        out["reference_preprocessing"] = dict(raw_observed=True, size_filter=True, exclude_gold=True)
        out["preprocessing_details"] = details
    output = args.output or DATA / ("audit_exact_columns_raw_wordlike.json" if args.raw_wordlike
                                    else "audit_exact_columns.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2) + "\n")
    brief = {k: v for k, v in out.items() if k not in ("inputs", "page_distributions", "bounds")}
    brief["bounds_log10"] = {base: row["log10_upper_bound"] for base, row in out["bounds"].items()}
    brief["exact_rational_artifact"] = str(output)
    print(json.dumps(brief, indent=2))


if __name__ == "__main__":
    main()
