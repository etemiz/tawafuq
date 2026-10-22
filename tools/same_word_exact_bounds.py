"""Exact-rational expectation checks and conservative decimal Hoeffding certificates.

These bounds concern the declared row-conditioned word-position models, not
text composition. Avoid floating-point log/exponential arithmetic in the
published conservative 10^-n certificates.
"""
import argparse
from collections import Counter
from fractions import Fraction
import json
import math
from pathlib import Path

import numpy as np

from same_word_alignment import OUTPUT as SOURCE, canonical_inventory, geometry_edges, strata, digest
from semantic_validation import DATA, is_name

OUTPUT = DATA / "research_same_word_exact_bounds_v1.json"


def exact_expectation(selected, groups, left, right):
    sizes, counts = Counter(groups.tolist()), Counter(groups[np.asarray(selected, dtype=bool)].tolist())
    neighbors = [Counter() for _ in selected]
    for i, j in zip(left.tolist(), right.tolist()):
        if groups[i] == groups[j]:
            raise AssertionError("row-contained independent strata required")
        neighbors[i][int(groups[j])] += 1
        neighbors[j][int(groups[i])] += 1
    expected, cached = Fraction(0), {}
    for i, group in enumerate(groups.tolist()):
        if not counts[group]:
            continue
        avoid = Fraction(1)
        for other, potential in neighbors[i].items():
            key = sizes[other], counts[other], potential
            if key not in cached:
                n, k, m = key
                cached[key] = Fraction(math.comb(n-m, k), math.comb(n, k)) if n-m >= k else Fraction(0)
            avoid *= cached[key]
        expected += Fraction(counts[group], sizes[group])*(1-avoid)
    return expected


def certificate(observed, mean, squared_ranges):
    """Use mu<=ceil(mu) and ln(10)<2303/1000, both checked exactly.

    A finite positive-term exponential series at 2303/1000 is already >10,
    proving the stated strict upper bound for ln(10). Hoeffding then gives
    P(T>=t)<=exp(-2(t-mu)^2 / sum k_page^2).
    """
    logarithm_upper = Fraction(2303, 1000)
    exponential_lower = sum((logarithm_upper**j/Fraction(math.factorial(j)) for j in range(31)), Fraction(0))
    if exponential_lower <= 10:
        raise AssertionError("ln(10) rational upper-bound proof failed")
    rounded_mean = math.ceil(mean)
    gap = max(0, observed-rounded_mean)
    exponent = Fraction(2*gap*gap, squared_ranges) if squared_ranges else Fraction(0)
    power = int(exponent/logarithm_upper)
    if power and exponent < power*logarithm_upper:
        raise AssertionError("decimal tail certificate failed")
    return dict(expectation_numerator_hex=hex(mean.numerator), expectation_denominator_hex=hex(mean.denominator),
                expectation_integer_upper_bound=rounded_mean, observed=observed, sum_squared_page_ranges=squared_ranges,
                conservative_decimal_power=power,
                statement=f"P(T >= {observed}) < 10^-{power}" if power else "No nontrivial decimal bound certified",
                proof="Exact rational mean <= integer ceiling. ln(10)<2303/1000 certified by a 31-term rational exponential partial sum >10. Compare 2*(observed-ceiling)^2/sum_squared_page_ranges with power*2303/1000. Hoeffding uses independent page scores in [0,k_page].")


def analyze():
    report = json.loads(SOURCE.read_text())
    canonical, _ = canonical_inventory()
    inventory = report["views"]["conservative_v5"]["located_inventory"]
    rows = [dict(t=t, page=p, row=r, x2=x, width=w) for t, p, r, x, w in inventory]
    left, right = geometry_edges(rows, report["spec"]["tolerance_pixels"])
    result = {}
    for model, compared in report["views"]["conservative_v5"]["comparisons"].items():
        groups = strata(rows, model, report["spec"]["width_bin"])
        metrics = {}
        for metric in ("standalone_allah", "allah_name_family"):
            selected = np.array([canonical[r["t"]]["word"] == "الله" if metric == "standalone_allah" else
                                 is_name(canonical[r["t"]]["form"]) for r in rows], dtype=bool)
            mean = exact_expectation(selected, groups, left, right)
            source = compared["metrics"][metric]
            if abs(float(mean)-source["analytic_expected_aligned"]) > 1e-9:
                raise AssertionError("exact and floating analytic expectations disagree")
            per_page = Counter(r["page"] for r, yes in zip(rows, selected) if yes)
            ranges = sum(k*k for k in per_page.values())
            if ranges != source["sum_squared_page_ranges"]:
                raise AssertionError("independent-page score ranges differ")
            observed = report["views"]["conservative_v5"]["targets"][metric]["aligned"]
            metrics[metric] = certificate(observed, mean, ranges)
        result[model] = metrics
    return dict(version="same-word-exact-expectation-hoeffding-certificates-v1", certificates=result,
        inputs={p.name: digest(p) for p in (SOURCE, Path(__file__), Path(__file__).with_name("same_word_alignment.py"))},
        caveat="Exact arithmetic certifies conservative decimal Hoeffding bounds under the already declared conditional word-position models. These are upper bounds, not exact tails or probabilities of Quranic composition/divinity. Location accuracy, missing words and observational model selection remain outside this mathematical certificate.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build", action="store_true")
    modes.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    report = analyze()
    if args.verify:
        if report != json.loads(OUTPUT.read_text()):
            raise AssertionError("exact same-word certificates differ")
        print("PASS exact-rational same-word expectations and integer-certified decimal tail bounds")
    else:
        OUTPUT.write_text(json.dumps(report, indent=2)+"\n")
    for model, metrics in report["certificates"].items():
        for metric, row in metrics.items():
            print(model, metric, "mean <=", row["expectation_integer_upper_bound"], row["statement"])
