"""Independent exhaustive word/phrase and coherent-packing ground truths."""
from itertools import permutations, product
import unittest

import numpy as np

import broad_phrase_alignment as bp


class BroadPhraseTests(unittest.TestCase):
    def test_windows_are_within_verse_and_keep_exact_identity(self):
        canonical = {i: dict(t=i, verse="2:1" if i < 3 else "2:2", word=w, form=w)
                     for i, w in enumerate(("أ", "ا", "ب", "أ", "ا", "ب"))}
        self.assertEqual(bp.windows(canonical, 2), [(0, ("أ", "ا")), (1, ("ا", "ب")),
                                                    (3, ("أ", "ا")), (4, ("ا", "ب"))])
        self.assertEqual(bp.windows(canonical, 4), [])

    def test_inventory_accounts_for_missing_row_split_and_order(self):
        text = ("الله", "x")*5
        canonical = {i: dict(t=i, verse=str(i//2), word=w, form=w) for i, w in enumerate(text)}
        words = [dict(t=i, page=1, row=i//2 if i!=5 else 8, x2=100 if i%2==0 else 40,
                      bbox=[0, 0, 20, 40], width=20) for i in range(10) if i!=3]
        words[-1]["x2"] = 101
        inv = bp.inventory(canonical, words, 2, set(range(len(words))), set(range(10)))
        self.assertEqual([r[2] for r in inv["ledger"]],
                         ["located", "missing_constituent", "cross_row", "located", "reversed_or_duplicate_centers"])
        self.assertFalse(inv["non_allah"][0])
        self.assertEqual(len(inv["occurrences"]), 2)

    def test_corresponding_words_not_only_phrase_center(self):
        # Both phrases have the same midpoint, but corresponding words differ
        # by 20px: hull-center coincidence must not pass the strict statistic.
        indices = np.array([[0, 1], [2, 3]])
        x2 = np.array([200, 0, 160, 40])
        marked, match = bp.aligned(x2, indices, np.array([0]), np.array([1]))
        self.assertFalse(marked.any())
        self.assertFalse(match.any())
        x2 = np.array([200, 0, 170, 30])
        self.assertTrue(bp.aligned(x2, indices, np.array([0]), np.array([1]))[0].all())

    def test_all_tiny_coordinates_against_scalar_phrase_oracle(self):
        occurrences = [dict(page=1, row=0, label=0), dict(page=1, row=1, label=0),
                       dict(page=1, row=1, label=0), dict(page=2, row=0, label=0),
                       dict(page=1, row=2, label=1)]
        left, right = bp.candidates(occurrences)
        self.assertEqual(list(zip(left.tolist(), right.tolist())), [(0, 1), (0, 2)])
        indices = np.arange(10).reshape(5, 2)
        for values in product((0, 30, 31), repeat=6):
            positions = np.array(list(values)+[0]*4)
            expected = set()
            for i, j in ((0, 1), (0, 2)):
                if all(abs(positions[indices[i, k]]-positions[indices[j, k]]) <= 30 for k in range(2)):
                    expected.update((i, j))
            marked, _ = bp.aligned(positions, indices, left, right)
            self.assertEqual(set(np.flatnonzero(marked)), expected)

    def test_vectorized_segmented_packing_every_gap_arrangement(self):
        widths = ([5, 10, 20, 3], [4, 8, 6])
        original_gaps = ([1, 3, 1], [0, 5])
        words, rows = [], []
        for y, (ws, gs) in enumerate(zip(widths, original_gaps)):
            right = 100+y*20
            extent_left = right-sum(ws)-sum(gs)
            ids = []
            for width in ws:
                ids.append(len(words))
                words.append(dict(width=width))
            rows.append(dict(eligible=True, extent=[extent_left, right], word_indices=ids, gaps_rtl=gs))
        packing = bp.packer(words, dict(pages=[dict(rows=rows)]))
        for a in set(permutations(original_gaps[0])):
            for b in set(permutations(original_gaps[1])):
                actual = bp.packed_centers(packing, np.array(a+b))
                expected = []
                for widths_row, gaps_row, row in zip(widths, (a, b), rows):
                    edge = row["extent"][0]
                    centers = []
                    for i in range(len(widths_row)-1, -1, -1):
                        centers.append(2*edge+widths_row[i])
                        edge += widths_row[i]+(gaps_row[i-1] if i else 0)
                    self.assertEqual(edge, row["extent"][1])
                    expected.extend(centers[::-1])
                np.testing.assert_array_equal(actual, expected)


if __name__ == "__main__":
    unittest.main()
