import itertools
import unittest
from collections import Counter
from fractions import Fraction

import numpy as np

from alignment import reference_flags
from exact_column import column_distribution, markov_bound


class ExactColumnTests(unittest.TestCase):
    def test_page_distribution_by_all_subsets(self):
        slots = np.array([(0, 100), (0, 101), (1, 100), (0, 300), (1, 301), (2, 300)], dtype=float)
        for k in range(len(slots) + 1):
            expected = Counter()
            for pick in itertools.combinations(range(len(slots)), k):
                col, _ = reference_flags({1: slots[list(pick)]})[1]
                expected[int(col.sum())] += 1
            counts, denominator = column_distribution(slots, k)
            self.assertEqual(counts, [expected[a] for a in range(k + 1)])
            self.assertEqual(sum(expected.values()), denominator)

    def test_exact_markov_bounds_dominate_exact_joint_tail(self):
        # Page PMF: X=0 with probability 2/3; X=2 with probability 1/3.
        d = ([2, 0, 1], 3)
        for threshold in range(5):
            actual = sum(Fraction(na * nb, 9) for a, na in enumerate(d[0])
                         for b, nb in enumerate(d[0]) if a + b >= threshold)
            for base in (2, 3, 4, 8):
                self.assertLessEqual(actual, markov_bound([d, d], threshold, base))


if __name__ == "__main__":
    unittest.main()
