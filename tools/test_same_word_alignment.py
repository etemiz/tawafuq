"""Independent pair enumeration and exact permutation oracles for word geometry."""
import itertools
import unittest
from collections import Counter

import numpy as np

from same_word_alignment import spelling, geometry_edges, flags, analytic_means, permute, locate


class SameWordAlignmentTests(unittest.TestCase):
    def test_spelling_retains_prefix_hamza_and_letter_distinctions(self):
        self.assertEqual(spelling("ٱللَّهِ"), "الله")
        self.assertNotEqual(spelling("وَٱللَّهِ"), spelling("ٱللَّهِ"))
        self.assertNotEqual(spelling("أَنَّ"), spelling("إِنَّ"))
        self.assertNotEqual(spelling("رَحْمَةٌ"), spelling("رَحْمَهُ"))
        self.assertNotEqual(spelling("عَلَىٰ"), spelling("عَلِيٌّ"))

    def test_geometric_edges_inclusive_distance_rows_pages_and_half_pixels(self):
        rows = [dict(page=1, row=0, x2=200), dict(page=1, row=1, x2=230),
                dict(page=1, row=2, x2=231), dict(page=1, row=0, x2=210),
                dict(page=2, row=1, x2=200)]
        left, right = geometry_edges(rows, 15)
        actual = {frozenset((int(i), int(j))) for i, j in zip(left, right)}
        expected = {frozenset((i, j)) for i in range(len(rows)) for j in range(i)
                    if rows[i]["page"] == rows[j]["page"] and rows[i]["row"] != rows[j]["row"]
                    and abs(rows[i]["x2"]-rows[j]["x2"]) <= 30}
        self.assertEqual(actual, expected)
        self.assertIn(frozenset((0, 1)), actual)
        self.assertNotIn(frozenset((0, 2)), actual)

    def test_every_tiny_identity_assignment_endpoint_and_pair_score(self):
        rows = [dict(page=1, row=r, x2=x) for r in (0, 1) for x in (200, 220, 400)]
        left, right = geometry_edges(rows, 15)
        for labels in itertools.product(range(3), repeat=len(rows)):
            labels = np.array(labels)
            actual, pairs = flags(labels, left, right)
            expected = np.zeros(len(rows), bool)
            expected_pairs = 0
            for i in range(len(rows)):
                for j in range(i):
                    if (labels[i] == labels[j] and rows[i]["row"] != rows[j]["row"]
                            and abs(rows[i]["x2"]-rows[j]["x2"]) <= 30):
                        expected[i] = expected[j] = True
                        expected_pairs += 1
            np.testing.assert_array_equal(actual, expected)
            self.assertEqual(int(pairs.sum()), expected_pairs)

    def test_analytic_expectation_against_every_allowed_permutation(self):
        rows = [dict(page=1, row=r, x2=x) for r in (0, 1, 2) for x in (200, 220, 400)]
        labels = np.array([0, 0, 1, 0, 1, 2, 0, 0, 2])
        left, right = geometry_edges(rows, 15)
        for groups in (np.repeat(np.arange(3), 3), np.array([0, 0, 1, 2, 2, 3, 4, 4, 5])):
            indices = [np.flatnonzero(groups == g) for g in sorted(set(groups))]
            choices = [sorted(set(itertools.permutations(labels[ids].tolist()))) for ids in indices]
            totals, n = np.zeros(3), 0
            for selections in itertools.product(*choices):
                trial = labels.copy()
                for ids, selected in zip(indices, selections):
                    trial[ids] = selected
                marked, _ = flags(trial, left, right)
                totals += np.bincount(trial[marked], minlength=3)
                n += 1
            np.testing.assert_allclose(analytic_means(labels, groups, left, right, 3), totals/n, atol=1e-12)

    def test_family_can_align_different_prefixes_but_exact_words_cannot(self):
        labels = np.array([0, 1, 2])
        left, right = np.array([0, 1]), np.array([1, 2])
        exact, _ = flags(labels, left, right)
        family, _ = flags(labels, left, right, np.array([True, True, False]))
        self.assertFalse(exact.any())
        np.testing.assert_array_equal(family, [True, True, False])

    def test_permutation_preserves_word_counts_in_every_stratum(self):
        labels = np.array([0, 1, 0, 2, 2, 1, 3])
        groups = np.array([0, 0, 0, 1, 1, 1, 2])
        rng = np.random.default_rng(11)
        seen = set()
        for _ in range(100):
            trial = permute(labels, groups, rng)
            seen.add(tuple(trial))
            for g in set(groups):
                self.assertEqual(Counter(trial[groups == g]), Counter(labels[groups == g]))
        self.assertGreater(len(seen), 1)

    def test_unresolved_occurrences_are_retained_and_no_color_input_is_needed(self):
        canonical = {i: dict(t=i, verse="2:1", word="الله", form="الله") for i in range(4)}
        words = [dict(kind="verse", t=i, verse="2:1", form="الله", mandatory_regions=[i],
                      bbox=[10, 20, 40, 70], surface_match=i != 1) for i in range(3)]
        mapping = dict(pages=[dict(page=1, words=words, row_groups=[dict(seeds=[0, 1], ordered_indices=[0, 1])])])
        sites = dict(pages=[dict(page=1, words=words)])
        accepted, unresolved = locate(canonical, sites, mapping, exact_surface=True)
        self.assertEqual([r["t"] for r in accepted], [0])
        self.assertEqual({r["t"]: r["status"] for r in unresolved},
                         {1: "nonexact_surface", 2: "ambiguous_seeded_row", 3: "no_mapped_token"})


if __name__ == "__main__":
    unittest.main()
