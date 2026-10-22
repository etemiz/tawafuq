"""Independent small-case tests: python -m unittest discover -s tools -p 'test_alignment.py'."""
import itertools
import unittest

import numpy as np

from alignment import (ScoreSpec, batch_flags, reference_flags, sample_placements,
                       score_flags)
from audit_stats import tail_summary
from slot_expectation import avoid, expectation


class AlignmentTests(unittest.TestCase):
    def compare(self, p, spec=ScoreSpec()):
        p = {n: np.asarray(v, dtype=float).reshape(-1, 2) for n, v in p.items()}
        ref = reference_flags(p, spec)
        got = batch_flags({n: v[None, ...] for n, v in p.items()}, spec)
        for n in p:
            for a, b in zip(ref[n], got[n]):
                np.testing.assert_array_equal(a, b[0])
        count = int(score_flags(got)["aligned"][0])
        self.assertLessEqual(count, sum(map(len, p.values())))
        return got, count

    def test_union_not_incidence_count(self):
        got, count = self.compare({1: [(0, 500), (1, 500)],
                                   2: [(0, 524), (1, 524)]})
        self.assertEqual(count, 4)
        self.assertEqual(int(score_flags(got)["overlap"][0]), 4)

    def test_no_missing_page_bridge(self):
        _, count = self.compare({1: [(0, 500)], 3: [(0, 500)]})
        self.assertEqual(count, 0)

    def test_both_endpoints_and_even_occupancy(self):
        got, count = self.compare({1: [(0, 100)], 2: [(0, 924), (0, 924)]})
        self.assertEqual(count, 3)
        self.assertTrue(got[1][1][0, 0])

    def test_same_line_is_not_column(self):
        _, count = self.compare({1: [(0, 300), (0, 301)]})
        self.assertEqual(count, 0)

    def test_bins_are_not_distance_windows(self):
        _, count = self.compare({1: [(0, 55.9), (1, 56.0)]})
        self.assertEqual(count, 0)

    def test_pairing_conventions(self):
        p = {1: [(0, 100)], 2: [(0, 924)], 3: [(0, 100)]}
        for pairing, expected in (("adjacent", 3), ("facing", 2), ("leaf", 2), ("none", 0)):
            _, count = self.compare(p, ScoreSpec(pairing=pairing))
            self.assertEqual(count, expected)

    def test_exhaustive_tiny_subsets(self):
        slots = [(0, 26), (0, 56), (1, 26), (1, 56)]
        subsets = [list(c) for k in range(5) for c in itertools.combinations(slots, k)]
        for a, b in itertools.product(subsets, repeat=2):
            self.compare({1: a, 2: [(l, 1024 - x) for l, x in b]})

    def test_random_batches_against_reference(self):
        rng = np.random.default_rng(41)
        pages = {n: dict(reds=np.zeros((n % 4, 2)), slots=np.column_stack(
            (rng.integers(0, 4, 13), rng.uniform(0, 1024, 13)))) for n in (1, 2, 4, 5)}
        draws = sample_placements(pages, rng, 20)
        got = batch_flags(draws)
        for b in range(20):
            ref = reference_flags({n: p[b] for n, p in draws.items()})
            for n in pages:
                for expected, actual in zip(ref[n], got[n]):
                    np.testing.assert_array_equal(expected, actual[b])

    def test_zero_exceedance_uncertainty(self):
        s = tail_summary(10, np.zeros(400))
        self.assertEqual(s["exceedances"], 0)
        self.assertAlmostEqual(s["plus_one_mc"], 1 / 401)
        self.assertAlmostEqual(s["tail_upper_one_sided"], 1 - 0.05 ** (1 / 400))
        self.assertIsNone(s["descriptive_z"])

    def test_legacy_run_returns_real_curves_for_both_modes(self):
        from real_stats import run, simulate
        slots = np.array([(0, 100), (1, 100), (0, 500), (1, 500)], dtype=float)
        pages = {1: dict(reds=slots[:2], slots=slots, nlines=2)}
        totals, aligned, curves = run(pages, "null", reps=3)
        np.testing.assert_array_equal(totals, [2, 2, 2])
        np.testing.assert_array_equal(curves.sum(axis=1), [1, 1, 1])
        np.testing.assert_array_equal(aligned, simulate(pages, 3)["aligned"])
        _, observed, curve = run(pages, "observed")
        self.assertEqual(observed[0], 2)
        self.assertEqual(curve[0, 2], 1)

    def test_analytic_mean_by_full_enumeration(self):
        sa = np.array([(0, 100), (1, 100), (0, 300), (1, 500)], dtype=float)
        sb = np.array([(0, 924), (1, 924), (0, 724), (1, 524)], dtype=float)
        pages = {1: dict(reds=sa[:2], slots=sa), 2: dict(reds=sb[:2], slots=sb)}
        for pairing in ("adjacent", "facing", "leaf", "none"):
            spec = ScoreSpec(pairing=pairing)
            exact, _ = expectation(pages, spec)
            sums = dict.fromkeys(exact, 0)
            count = 0
            for a, b in itertools.product(itertools.combinations(sa, 2), itertools.combinations(sb, 2)):
                flags = reference_flags({1: a, 2: b}, spec)
                for col, mir in flags.values():
                    sums["column"] += int(col.sum())
                    sums["mirror"] += int(mir.sum())
                    sums["overlap"] += int((col & mir).sum())
                    sums["aligned"] += int((col | mir).sum())
                count += 1
            for key in exact:
                self.assertAlmostEqual(exact[key], sums[key] / count)
        self.assertEqual(avoid(5, 3, 3), 0)
        self.assertEqual(avoid(0, 0, 0), 1)

    def test_line_stratified_mean_by_enumeration(self):
        sa = np.array([(0, 100), (0, 500), (1, 100), (1, 500)], dtype=float)
        sb = np.array([(0, 924), (0, 524), (1, 924), (1, 524)], dtype=float)
        pages = {1: dict(reds=sa[[0, 2]], slots=sa), 2: dict(reds=sb[[0, 2]], slots=sb)}
        analytic, _ = expectation(pages, null_model="line")
        total = dict.fromkeys(analytic, 0)
        draws = list(itertools.product((0, 1), (2, 3)))
        for a, b in itertools.product(draws, repeat=2):
            ref = reference_flags({1: sa[list(a)], 2: sb[list(b)]})
            flags = {n: (c[None], m[None]) for n, (c, m) in ref.items()}
            for k, v in score_flags(flags).items():
                total[k] += int(v[0])
        for k in total:
            self.assertAlmostEqual(analytic[k], total[k] / len(draws) ** 2)
        sampled = sample_placements(pages, np.random.default_rng(3), 20, "line")
        for n in pages:
            np.testing.assert_array_equal(sampled[n][:, :, 0], np.tile([0, 1], (20, 1)))


if __name__ == "__main__":
    unittest.main()
