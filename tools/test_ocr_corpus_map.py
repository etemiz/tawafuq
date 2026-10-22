"""Independent tiny substring/edit-path ground truths for corpus anchoring."""
import itertools
import unittest
from functools import lru_cache

import numpy as np

from ocr_corpus_map import (Spec, edit_table, retrieve, semiglobal_support,
                            unique_index, virtual_corpus)
from ocr_line_map import costs


@lru_cache(None)
def paths(a, b):
    if not a:
        return [(len(b), (None,) * len(b))]
    if not b:
        return [(len(a), ())]
    options = []
    options.extend((cost + 1, tuple(None if i is None else i + 1 for i in mapping))
                   for cost, mapping in paths(a[1:], b))
    options.extend((cost + 1, (None,) + mapping) for cost, mapping in paths(a, b[1:]))
    options.extend((cost + (a[0] != b[0]), (0,) + tuple(None if i is None else i + 1 for i in mapping))
                   for cost, mapping in paths(a[1:], b[1:]))
    optimum = min(c for c, _ in options)
    return [x for x in options if x[0] == optimum]


class CorpusMapTests(unittest.TestCase):
    def test_vectorized_table_matches_scalar_global_recurrence(self):
        strings = ["".join(t) for n in range(4) for t in itertools.product("ab", repeat=n)]
        for a, b in itertools.product(strings, repeat=2):
            np.testing.assert_array_equal(edit_table(a, b, False), costs(a, b))

    def test_all_substring_paths_with_grouped_words_and_regions(self):
        strings = ["".join(t) for n in range(1, 4) for t in itertools.product("ab", repeat=n)]
        for reference, observed in itertools.product(strings, repeat=2):
            alternatives = []
            for lo in range(len(reference) + 1):
                for hi in range(lo, len(reference) + 1):
                    alternatives.extend((cost, tuple(None if i is None else lo + i for i in mapping))
                                        for cost, mapping in paths(reference[lo:hi], observed))
            optimum = min(c for c, _ in alternatives)
            mappings = [p for c, p in alternatives if c == optimum]
            for ref_words in ([reference], list(reference)):
                word_of = [i for i, word in enumerate(ref_words) for _ in word]
                for regions in ([observed], list(observed)):
                    found = semiglobal_support(ref_words, regions)
                    self.assertEqual(found["edit_cost"], optimum)
                    start = 0
                    for region, row in zip(regions, found["regions"]):
                        end = start + len(region)
                        owners = sorted({word_of[i] for mapping in mappings for i in mapping[start:end]
                                         if i is not None})
                        inserted = any(all(i is None for i in mapping[start:end]) for mapping in mappings)
                        self.assertEqual(row["candidate_words"], owners)
                        self.assertEqual(row["whole_region_insertion_possible"], inserted)
                        self.assertEqual(row["mandatory_word"], owners[0] if len(owners) == 1 and not inserted else None)
                        start = end

    def test_repeated_reference_substrings_are_ambiguous(self):
        result = semiglobal_support(["a", "b", "a", "b"], ["a", "b"])
        self.assertEqual(result["optimal_reference_startpoints"], [0, 2])
        self.assertTrue(all(r["mandatory_word"] is None for r in result["regions"]))

    def test_free_reference_ends_do_not_make_ocr_noise_free(self):
        result = semiglobal_support(["prefix", "abc", "suffix"], ["!", "abc", "?"])
        self.assertEqual(result["edit_cost"], 2)
        self.assertEqual(result["regions"][1]["mandatory_word"], 1)

    def test_anchor_must_lie_on_an_optimal_alignment(self):
        result = semiglobal_support(["abc", "xxx", "abcde"], ["abcde"], [(0, 0, 3), (6, 0, 5)])
        self.assertEqual(result["edit_cost"], 0)
        self.assertEqual(result["optimal_exact_anchors"], [(6, 0, 5)])

    def test_unencoded_basmalas_keep_canonical_ids_and_exclude_surah_nine(self):
        tokens, _, _ = virtual_corpus([(1, 1, ["بسم", "الله"]), (2, 1, ["الم"]), (9, 1, ["براءه"])])
        self.assertEqual([t["t"] for t in tokens if t["kind"] == "verse"], [0, 1, 2, 3])
        self.assertEqual([t["verse"] for t in tokens if t["kind"] == "surah_head_basmala"], ["2:0"] * 4)

    def test_unique_anchors_exclude_repeated_text_and_retrieve_without_page_ids(self):
        reference = "prefixabcdefghijklmnopqrstuvsuffix"
        spec = Spec(anchor_length=4, minimum_anchor_coverage=12, minimum_anchor_advantage=4)
        result = retrieve("abcdefghijklmnopqrstuv", reference, unique_index(reference, 4), spec)
        self.assertEqual(result["status"], "retrieved")
        self.assertNotIn("aaaa", unique_index("aaaaaa", 4))
        self.assertEqual(retrieve("aaaa", reference, unique_index(reference, 4), spec)["status"], "no_unique_anchor")


if __name__ == "__main__":
    unittest.main()
