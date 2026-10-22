import itertools
import unittest
from fractions import Fraction

import numpy as np

from same_word_alignment import geometry_edges, flags
from same_word_exact_bounds import exact_expectation, certificate


class SameWordExactBoundTests(unittest.TestCase):
    def test_exact_expectation_by_every_allowed_selection(self):
        rows = [dict(page=1, row=r, x2=x) for r in (0, 1, 2) for x in (200, 220, 400)]
        groups = np.repeat(np.arange(3), 3)
        selected = np.array([True, False, False, True, True, False, True, False, False])
        left, right = geometry_edges(rows, 15)
        expected, n = 0, 0
        for a, b, c in itertools.product(itertools.combinations(range(3), 1),
                                       itertools.combinations(range(3, 6), 2),
                                       itertools.combinations(range(6, 9), 1)):
            trial = np.zeros(9, dtype=np.int32)
            trial[list(a+b+c)] = 1
            marked, _ = flags(trial, left, right, np.array([False, True]))
            expected += int(marked.sum())
            n += 1
        self.assertEqual(exact_expectation(selected, groups, left, right), Fraction(expected, n))

    def test_certificate_rounds_mean_up_and_proves_conservative_power(self):
        row = certificate(1717, Fraction(7950405554494089, 10**13), 12895)
        self.assertEqual(row["expectation_integer_upper_bound"], 796)
        self.assertEqual(row["conservative_decimal_power"], 57)
        self.assertEqual(certificate(1, Fraction(3, 2), 10)["conservative_decimal_power"], 0)


if __name__ == "__main__":
    unittest.main()
