"""Independent all-subset optimality and null-probability checks."""
import itertools
import unittest
from fractions import Fraction

import numpy as np

from alignment import ScoreSpec, reference_flags
from constructive_selection import maximize_columns, maximum_event_probability


class ConstructiveSelectionTests(unittest.TestCase):
    def test_every_tiny_geometry_and_every_draw_count(self):
        # A 2-line, 3-column frame; every possible fixed-site subset and k.
        frame = [(line, x) for line in (0, 1) for x in (100, 200, 300)]
        for present in itertools.product((False, True), repeat=len(frame)):
            slots = np.array([p for p, yes in zip(frame, present) if yes], dtype=float).reshape(-1, 2)
            for k in range(len(slots)+1):
                scored = []
                for choice in itertools.combinations(range(len(slots)), k):
                    flags = reference_flags({1: slots[list(choice)]})[1][0]
                    scored.append(int(flags.sum()))
                result = maximize_columns(slots, k)
                selected = result["selected_indices"]
                actual = int(reference_flags({1: slots[selected]})[1][0].sum())
                self.assertEqual(len(selected), k)
                self.assertEqual(len(set(selected)), k)
                self.assertEqual(result["maximum_column_score"], max(scored))
                self.assertEqual(actual, max(scored))

    def test_duplicate_sites_are_distinct_but_same_line_is_not_a_partner(self):
        slots = np.array([(0, 100), (0, 100), (0, 100), (1, 100), (1, 300)], dtype=float)
        for k in range(2, 5):
            self.assertEqual(maximize_columns(slots, k)["maximum_column_score"], k)
        single = slots[:3]
        self.assertEqual(maximize_columns(single, 3)["maximum_column_score"], 0)

    def test_nondefault_clipping_and_stable_witnesses(self):
        spec = ScoreSpec(column_origin=0, column_width=10, bins=2)
        slots = np.array([(0, -10), (1, 0), (0, 20), (1, 100), (2, 101)], dtype=float)
        for k in range(6):
            result = maximize_columns(slots, k, spec)
            maxima = [int(reference_flags({1: slots[list(c)]}, spec)[1][0].sum())
                      for c in itertools.combinations(range(len(slots)), k)]
            self.assertEqual(result["maximum_column_score"], max(maxima))
            self.assertEqual(result, maximize_columns(slots, k, spec))

    def test_global_maximum_probability_by_independent_enumeration(self):
        distributions = {"1": dict(counts=[2, 0, 1], denominator=3),
                         "2": dict(counts=[3, 0, 3], denominator=6)}
        actual = Fraction(0)
        for a, b in itertools.product(range(3), repeat=2):
            if a+b == 4:
                actual += Fraction(distributions["1"]["counts"][a]*distributions["2"]["counts"][b], 18)
        self.assertEqual(maximum_event_probability(distributions), actual)
        self.assertEqual(actual, Fraction(1, 6))

    def test_invalid_draws_and_geometry(self):
        slots = np.array([(0, 100), (1, 100)], dtype=float)
        for k in (-1, 3, 1.5, True):
            with self.assertRaises(ValueError):
                maximize_columns(slots, k)
        for bad in (np.array([[0, float("nan")]]), np.array([[0.5, 100]]), np.array([[-1, 100]])):
            with self.assertRaises(ValueError):
                maximize_columns(bad, 1)


if __name__ == "__main__":
    unittest.main()
