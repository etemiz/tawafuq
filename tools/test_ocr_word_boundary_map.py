"""Independent exhaustive path oracle for the bounded word-edit lattice."""
from functools import lru_cache
import itertools
import unittest

from ocr_benchmark import edit_counts
from ocr_word_boundary_map import WordSpec, word_support


@lru_cache(None)
def global_paths(reference, observed, scale=4, penalty=1, maximum=3):
    if not reference:
        return [(sum(map(len, observed))*scale, (frozenset(),)*len(observed))]
    if not observed:
        return [(sum(map(len, reference))*scale, ())]
    options = []
    for cost, owners in global_paths(reference[1:], observed, scale, penalty, maximum):
        options.append((cost+len(reference[0])*scale, tuple(frozenset(i+1 for i in s) for s in owners)))
    for cost, owners in global_paths(reference, observed[1:], scale, penalty, maximum):
        options.append((cost+len(observed[0])*scale, (frozenset(),)+owners))
    for p in range(1, min(maximum, len(reference))+1):
        for q in range(1, min(maximum, len(observed))+1):
            if p != 1 and q != 1:
                continue
            edge = scale*edit_counts("".join(reference[:p]), "".join(observed[:q]))["distance"] + penalty*(p+q-2)
            for cost, owners in global_paths(reference[p:], observed[q:], scale, penalty, maximum):
                options.append((cost+edge, (frozenset(range(p)),)*q
                                + tuple(frozenset(i+p for i in s) for s in owners)))
    optimum = min(c for c, _ in options)
    return [x for x in options if x[0] == optimum]


class WordBoundaryTests(unittest.TestCase):
    def test_all_word_substrings_and_optimal_group_paths(self):
        sequences = [t for n in range(3) for t in itertools.product(("a", "b", "ab"), repeat=n)]
        for reference, observed in itertools.product(sequences, repeat=2):
            alternatives = []
            for lo in range(len(reference)+1):
                for hi in range(lo, len(reference)+1):
                    alternatives.extend((cost, tuple(frozenset(i+lo for i in s) for s in owners))
                                        for cost, owners in global_paths(reference[lo:hi], observed))
            optimum = min(c for c, _ in alternatives)
            paths = [owners for c, owners in alternatives if c == optimum]
            found = word_support(reference, observed)
            self.assertEqual(found["edit_cost"], optimum, (reference, observed))
            for j, row in enumerate(found["regions"]):
                choices = sorted(set().union(*(p[j] for p in paths)))
                inserted = any(not p[j] for p in paths)
                self.assertEqual(row["candidate_words"], choices, (reference, observed, j))
                self.assertEqual(row["whole_region_insertion_possible"], inserted)
                self.assertEqual(row["mandatory_word"], choices[0] if len(choices) == 1 and not inserted else None)

    def test_split_prefix_and_merged_words_keep_geometry_ambiguity(self):
        split = word_support(["والله"], ["و", "الله"])
        self.assertEqual(split["edit_cost"], 1)
        self.assertEqual([r["mandatory_word"] for r in split["regions"]], [0, 0])
        merged = word_support(["على", "الله"], ["علىالله"])
        self.assertEqual(merged["edit_cost"], 1)
        self.assertEqual(merged["regions"][0]["candidate_words"], [0, 1])
        self.assertIsNone(merged["regions"][0]["mandatory_word"])

    def test_reverse_costs_preserve_original_chunk_spelling(self):
        result = word_support(["ab", "cd"], ["abcd"])
        self.assertEqual(result["edit_cost"], 1)
        self.assertEqual(result["regions"][0]["candidate_words"], [0, 1])

    def test_repeated_words_remain_ambiguous_without_context(self):
        result = word_support(["الله", "رب", "الله"], ["الله"])
        self.assertEqual(result["edit_cost"], 0)
        self.assertEqual(result["regions"][0]["candidate_words"], [0, 2])
        self.assertIsNone(result["regions"][0]["mandatory_word"])

    def test_exact_boundaries_avoid_free_letter_exchange(self):
        words = ["الله", "لا", "اله", "الا", "هو"]
        result = word_support(words, words)
        self.assertEqual(result["edit_cost"], 0)
        self.assertEqual([r["mandatory_word"] for r in result["regions"]], list(range(5)))
        grouped = word_support(["abc"], ["a", "b", "c"], WordSpec())
        self.assertEqual(grouped["edit_cost"], 2)


if __name__ == "__main__":
    unittest.main()
