import itertools
import unittest
import numpy as np

from pair_statistics import word_cell_pairs
from grain_sweep import make_cells
from phrase_mirror_test import pair_stats, NBINS


class PairTests(unittest.TestCase):
    def test_counts_against_pair_enumeration(self):
        items = [(w, p, 0, c) for w in ("a", "b") for p in (1, 2) for c in (0, 1, 2)]
        for chosen in itertools.combinations(items, 4):
            for nb in (None, 3):
                expected = sum(a[0] == b[0] and a[1] != b[1] and a[2] == b[2]
                               and (a[3] == b[3] if nb is None else a[3] + b[3] == nb - 1)
                               for a, b in itertools.combinations(chosen, 2))
                self.assertEqual(word_cell_pairs(chosen, nb), expected)

    def test_fine_cells_do_not_collapse(self):
        cells, nb = make_cells([dict(page=1, yc=1500, xc=900), dict(page=2, yc=1600, xc=1000)], 56, 15)
        self.assertGreater(cells[0][1], 14)
        self.assertGreater(cells[0][2], 31)
        self.assertNotEqual(cells[0][1:], cells[1][1:])

    def test_mirror_is_not_global_relabeling(self):
        items = [("a", 1, 0, 0), ("a", 2, 0, 3)]
        self.assertEqual(word_cell_pairs(items), 0)
        self.assertEqual(word_cell_pairs(items, 4), 1)

    def test_phrase_pairs_against_direct_enumeration(self):
        items = [(1, 0, 0, 0), (2, 0, 0, 1), (3, 0, NBINS - 1, 1),
                 (2, 0, NBINS - 1, 1), (3, 0, 0, 0)]
        expected = [0, 0, 0, 0]
        for a, b in itertools.combinations(items, 2):
            if a[0] == b[0] or a[1] != b[1] or a[3] == b[3]:
                continue
            facing = abs(a[0] - b[0]) == 1 and min(a[0], b[0]) % 2 == 0
            if a[2] == b[2]:
                expected[0] += 1
                expected[2] += facing
            if a[2] + b[2] == NBINS - 1:
                expected[1] += 1
                expected[3] += facing
        self.assertEqual(pair_stats(items), tuple(expected))

    def test_optimized_phrase_counts_with_duplicates_and_central_mirror(self):
        rng = np.random.default_rng(42)
        for _ in range(50):
            items = [tuple(map(int, row)) for row in np.column_stack(
                (rng.integers(1, 5, 40), rng.integers(0, 3, 40),
                 rng.integers(0, 5, 40), rng.integers(0, 2, 40)))]
            expected = [0, 0, 0, 0]
            for a, b in itertools.combinations(items, 2):
                if a[0] == b[0] or a[1] != b[1] or a[3] == b[3]:
                    continue
                facing = abs(a[0] - b[0]) == 1 and min(a[0], b[0]) % 2 == 0
                if a[2] == b[2]:
                    expected[0] += 1
                    expected[2] += facing
                if a[2] + b[2] == 4:
                    expected[1] += 1
                    expected[3] += facing
            self.assertEqual(pair_stats(items, bins=5), tuple(expected))


if __name__ == "__main__":
    unittest.main()
