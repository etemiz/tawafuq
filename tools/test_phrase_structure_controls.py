"""Independent exhaustive oracles for verse/phrase-preserving gap controls."""
from collections import Counter
from itertools import permutations, product
import unittest

import numpy as np

import broad_phrase_alignment as bp
import phrase_structure_controls as pc


def frame():
    words, canonical, rows = [], {}, []
    for row_id in range(2):
        ids = []
        edge = 100
        widths = [10, 5, 8, 9, 7, 6]
        gaps = [1, 5, 12, 2, 7] if row_id == 0 else [7, 1, 12, 5, 2]
        for j, width in enumerate(widths):
            i = len(words)
            ids.append(i)
            word = ["a", "b", "c", "d", "e", "f"][j]
            canonical[i] = dict(t=i, word=word, form=word, verse="2:1" if j < 3 else "2:2")
            words.append(dict(t=i, word=word, width=width, page=1, row=row_id,
                              bbox=[edge-width, row_id*50, edge, row_id*50+40], x2=2*edge-width))
            edge -= width+(gaps[j] if j < len(gaps) else 0)
        rows.append(dict(eligible=True, row=row_id, word_indices=ids, token_ids=ids, gaps_rtl=gaps, extent=[edge, 100]))
    return canonical, words, dict(pages=[dict(page=1, rows=rows)])


def assignments(gaps, groups):
    indices = [np.flatnonzero(groups == g) for g in sorted(set(groups.tolist()))]
    choices = [set(permutations(gaps[ids].tolist())) for ids in indices]
    for combination in product(*choices):
        trial = gaps.copy()
        for ids, selected in zip(indices, combination):
            trial[ids] = selected
        yield trial


class StructureControlTests(unittest.TestCase):
    def test_longest_canonical_blocks_are_nonoverlapping(self):
        v = {2: {("a", "b"), ("b", "c")}, 3: {("a", "b", "c")}}
        self.assertEqual(pc.blocks(["a", "b", "c", "a", "b", "z"], v), [[0, 3], [3, 5], [5, 6]])
        self.assertEqual(pc.blocks(["x"], v), [[0, 1]])

    def test_verse_boundaries_fixed_in_every_allowed_layout(self):
        canonical, words, feasible = frame()
        packing = bp.packer(words, feasible)
        groups, details = pc.grouping(canonical, words, feasible, {}, "verse_internal")
        self.assertEqual([r["verse_boundary_gap_indices"] for r in details], [[2], [7]])
        for gaps in assignments(packing["gaps"], groups):
            self.assertEqual(gaps[2], 12)
            self.assertEqual(gaps[7], 12)
            for start in (0, 5):
                self.assertEqual(sum(gaps[start:start+2]), sum(packing["gaps"][start:start+2]))
                self.assertEqual(sum(gaps[start+3:start+5]), sum(packing["gaps"][start+3:start+5]))

    def test_phrase_internal_gaps_and_translation_are_preserved(self):
        canonical, words, feasible = frame()
        vocabulary = {2: {("a", "b"), ("d", "e")}}
        groups, details = pc.grouping(canonical, words, feasible, vocabulary, "repeated_phrase_blocks")
        self.assertEqual([d["repeated_block_internal_gap_indices"] for d in details], [[0, 3], [5, 8]])
        packing = bp.packer(words, feasible)
        # Each fragment has only one between-block gap: it becomes fixed too.
        for gaps in assignments(packing["gaps"], groups):
            np.testing.assert_array_equal(gaps, packing["gaps"])
            np.testing.assert_array_equal(bp.packed_centers(packing, gaps), [w["x2"] for w in words])

    def test_exact_center_extrema_equal_every_tiny_permutation(self):
        canonical, words, feasible = frame()
        packing = bp.packer(words, feasible)
        for model in pc.MODELS:
            groups, _ = pc.grouping(canonical, words, feasible, {2: {("a", "b")}}, model)
            observed = np.array([bp.packed_centers(packing, gaps) for gaps in assignments(packing["gaps"], groups)])
            lo, hi = pc.center_ranges(words, packing, groups)
            np.testing.assert_array_equal(lo, observed.min(axis=0))
            np.testing.assert_array_equal(hi, observed.max(axis=0))

    def test_guaranteed_phrase_certificate_against_all_layouts(self):
        canonical, words, feasible = frame()
        packing = bp.packer(words, feasible)
        groups, _ = pc.grouping(canonical, words, feasible, {}, "verse_internal")
        lo, hi = pc.center_ranges(words, packing, groups)
        p = dict(indices=np.array([[0, 1, 2], [6, 7, 8]]), sim_left=np.array([0]), sim_right=np.array([1]))
        guaranteed, _ = pc.guaranteed(p, lo, hi)
        actual = np.array([bp.aligned(bp.packed_centers(packing, gaps), p["indices"], p["sim_left"], p["sim_right"])[0]
                           for gaps in assignments(packing["gaps"], groups)])
        np.testing.assert_array_equal(guaranteed, actual.all(axis=0))
        lo[1], hi[1] = -100, 300
        self.assertFalse(pc.guaranteed(p, lo, hi)[0].any())

    def test_interleaved_strata_sampler_and_equalization(self):
        gaps, groups = np.array([1, 10, 7, 4, 10, 3]), np.array([4, 2, 4, 3, 2, 4])
        rng = np.random.default_rng(91)
        for _ in range(50):
            permuted = pc.permute_gaps(gaps, groups, rng)
            for g in set(groups.tolist()):
                self.assertEqual(Counter(permuted[groups == g]), Counter(gaps[groups == g]))
        equalized = pc.equal_gaps(gaps, groups)
        np.testing.assert_array_equal(equalized, [4, 10, 4, 4, 10, 3])
        for g in set(groups.tolist()):
            self.assertEqual(sum(equalized[groups == g]), sum(gaps[groups == g]))


if __name__ == "__main__":
    unittest.main()
