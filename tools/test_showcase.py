import itertools
import unittest
from fractions import Fraction

from showcase_audit import max_bin_tail, manual_census, DATA
from real_stats import load_all


class ShowcaseTests(unittest.TestCase):
    def test_visible_showcase_column_does_not_relabel_hu_as_allah(self):
        pages = load_all(first=422, last=422, data=DATA / "real_boxes_v3")
        result = manual_census(pages)
        self.assertEqual(result["lafzullah_total"], 16)
        self.assertEqual(result["best_component_count"], 12)
        self.assertEqual(result["best_bin_lafzullah"], 11)
        self.assertEqual(result["other_best_bin_words"], ["هو"])

    def test_exact_polynomial_against_all_subsets(self):
        population = [0, 0, 0, 1, 1, 2]
        for draws in range(7):
            for threshold in range(1, 5):
                subsets = list(itertools.combinations(range(6), draws))
                hits = sum(max((sum(population[i] == b for i in s) for b in range(3)), default=0)
                           >= threshold for s in subsets)
                self.assertEqual(max_bin_tail([3, 2, 1], draws, threshold), Fraction(hits, len(subsets)))


if __name__ == "__main__":
    unittest.main()
