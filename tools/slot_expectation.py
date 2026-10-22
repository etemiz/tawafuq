"""Analytic first moments and a rigorous column-score concentration bound.

Independent pages; k_p uniformly sampled distinct slots per page. For a
specified selected slot, no column partner and no mirrored neighbor are
independent events (they involve different pages). Hypergeometric avoidance
probabilities give first moments without Monte Carlo or a Gaussian model.
"""
import math

import numpy as np

from alignment import ScoreSpec, eligible_pair, encode


def avoid(population, hits, draws):
    """P(no hits) = C(population-hits, draws) / C(population, draws)."""
    if not (0 <= hits <= population and 0 <= draws <= population):
        raise ValueError("invalid hypergeometric parameters")
    if draws > population - hits:
        return 0.0
    # Short product, no large binomial coefficients and no cancellation in logs.
    return math.prod((population - hits - j) / (population - j)
                     for j in range(draws))


def expectation(pages, spec=ScoreSpec(), null_model="page"):
    encoded = {n: encode(n, d["slots"], spec) for n, d in pages.items()}
    totals = dict(column=0.0, mirror=0.0, overlap=0.0, aligned=0.0)
    by_page = {}
    for n, d in pages.items():
        k, size = len(d["reds"]), len(d["slots"])
        col_sum = mir_sum = both_sum = union_sum = 0.0
        if k:
            lines, cols, mirs = encoded[n]
            for li, cb, mb in zip(lines, cols, mirs):
                if null_model == "page":
                    other_line = int(np.count_nonzero((cols == cb) & (lines != li)))
                    no_col = avoid(size - 1, other_line, k - 1)
                    inclusion = k / size
                elif null_model == "line":
                    reds_lines = d["reds"][:, 0]
                    no_col = 1.0
                    for other in np.unique(lines):
                        if other == li:
                            continue
                        no_col *= avoid(int(np.count_nonzero(lines == other)),
                                        int(np.count_nonzero((lines == other) & (cols == cb))),
                                        int(np.count_nonzero(reds_lines == other)))
                    inclusion = np.count_nonzero(reds_lines == li) / np.count_nonzero(lines == li)
                else:
                    raise ValueError("unknown null model")
                no_mir = 1.0
                for q in (n - 1, n + 1):
                    if q not in pages or not eligible_pair(min(n, q), max(n, q), spec):
                        continue
                    ql, _, qm = encoded[q]
                    hits = int(np.count_nonzero((ql == li) & (qm == mb)))
                    if null_model == "page":
                        no_mir *= avoid(len(ql), hits, len(pages[q]["reds"]))
                    else:
                        no_mir *= avoid(int(np.count_nonzero(ql == li)), hits,
                                        int(np.count_nonzero(pages[q]["reds"][:, 0] == li)))
                col_sum += inclusion * (1 - no_col)
                mir_sum += inclusion * (1 - no_mir)
                both_sum += inclusion * (1 - no_col) * (1 - no_mir)
                union_sum += inclusion * (1 - no_col * no_mir)
        values = dict(column=col_sum, mirror=mir_sum,
                      overlap=both_sum, aligned=union_sum)
        by_page[n] = values
        for key, value in values.items():
            totals[key] += value
    return totals, by_page


def column_hoeffding(observed, mean, pages):
    """For independent X_p in [0,k_p], P(sum X_p >= obs) <= exp(-2t²/sum k_p²).

    This bound applies ONLY to the column score, not the adjacency-coupled
    union. It is conditional on the stated independent slot-placement model.
    """
    widths_squared = sum(len(d["reds"]) ** 2 for d in pages.values())
    if widths_squared == 0:
        return dict(log10_upper_bound=0.0, method="Hoeffding", sum_squared_ranges=0)
    t = max(0.0, observed - mean)
    return dict(log10_upper_bound=-2 * t * t / widths_squared / math.log(10),
                method="Hoeffding, independent per-page column scores in [0,k_p]",
                sum_squared_ranges=widths_squared,
                caveat="An upper bound under the slot model, not an exact p-value; "
                "no correction for exploratory selection is supplied.")
