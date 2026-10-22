import itertools
import unittest
from functools import lru_cache

import numpy as np
from rosette_map import align_global, reading_order, build_rosettes


def match_cost(num, expected):
    if num is None:
        return 1.2
    if num == expected:
        return 0.0
    return 1 + 0.35 * abs(len(str(num)) - len(str(expected))) + 0.004 * abs(num - expected)


class RosetteDPTests(unittest.TestCase):
    def test_rtl_order_survives_vertical_jitter(self):
        rows = [dict(cy=68, cx=100), dict(cy=72, cx=900), dict(cy=180, cx=500)]
        self.assertEqual([r["cx"] for r in reading_order(rows)], [900, 100, 500])

    def test_invalid_group_does_not_loop(self):
        with self.assertRaises(ValueError):
            build_rosettes(np.zeros((1, 2, 2)), np.array([[1, 2, 3, 4, 5, 0]]), np.array([1]))

    def test_optimal_cost_against_exhaustive_paths(self):
        expected = [1, 2, 3]
        for numbers in itertools.product((1, 2, None), repeat=3):
            for page_ids in ((1, 1, 1), (1, 2, 2), (1, 2, 3)):
                seq = [dict(num=x, page=p) for x, p in zip(numbers, page_ids)]

                @lru_cache(None)
                def best(i, j):
                    if i == 3 and j == 3:
                        return 0.0
                    candidates = []
                    if i < 3:
                        candidates.append(2.2 + best(i + 1, j))
                    if j < 3 and (i in (0, 3) or page_ids[i] != page_ids[i - 1]):
                        candidates.append(2.2 + best(i, j + 1))
                    if i < 3 and j < 3:
                        candidates.append(match_cost(numbers[i], expected[j]) + best(i + 1, j + 1))
                    return min(candidates)

                ra = align_global(seq, np.array(expected), np.ones(3), band=4)
                matched = [(i, j) for i, j in enumerate(ra) if j is not None]
                cost = (2.2 * (3 - len(matched)) * 2
                        + sum(match_cost(numbers[i], expected[j]) for i, j in matched))
                self.assertAlmostEqual(cost, best(0, 0))

    def test_exact_end_and_missing_suffix(self):
        seq = [dict(num=1, page=1), dict(num=2, page=1)]
        self.assertEqual(align_global(seq, np.array([1, 2, 3]), np.ones(3), band=4), [0, 1])
        self.assertIsNone(align_global(seq, np.arange(20), np.ones(20), band=4))


if __name__ == "__main__":
    unittest.main()
