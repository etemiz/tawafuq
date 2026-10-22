"""Check ambiguity against exhaustive optimal edit paths on tiny strings."""
import itertools
import unittest
from functools import lru_cache

from ocr_line_map import align_words


class OCRLineMapTests(unittest.TestCase):
    def test_exact_word_lines_and_cross_line_word_ambiguity(self):
        result, distance = align_words(["abc", "de"], ["abc", "de"])
        self.assertEqual(distance, 0)
        self.assertEqual([r["stable_line"] for r in result], [0, 1])
        result, _ = align_words(["abcd"], ["ab", "cd"])
        self.assertIsNone(result[0]["stable_line"])
        self.assertEqual(result[0]["line_candidates"], [0, 1])

    def test_repeated_text_and_wholly_deleted_word_stay_unresolved(self):
        result, _ = align_words(["a"], ["a", "a"])
        self.assertEqual(result[0]["line_candidates"], [0, 1])
        self.assertIsNone(result[0]["stable_line"])
        result, _ = align_words(["a", "b"], ["a"])
        self.assertTrue(result[1]["whole_word_deletion_possible"])
        self.assertIsNone(result[1]["stable_line"])

    def test_all_optimal_character_line_choices_by_full_path_enumeration(self):
        # Each reference character is one word. Enumerate every minimum-cost
        # edit path independently, rather than reusing forward/backward tables.
        @lru_cache(None)
        def paths(a, b):
            if not a:
                return [(len(b), ())]
            if not b:
                return [(len(a), (None,) * len(a))]
            options = []
            options.extend((cost + 1, (None,) + mapping) for cost, mapping in paths(a[1:], b))
            options.extend((cost + 1, tuple(None if j is None else j + 1 for j in mapping))
                           for cost, mapping in paths(a, b[1:]))
            options.extend((cost + (a[0] != b[0]), (0,) + tuple(None if j is None else j + 1 for j in mapping))
                           for cost, mapping in paths(a[1:], b[1:]))
            best = min(cost for cost, _ in options)
            return [x for x in options if x[0] == best]
        strings = ["".join(x) for n in range(1, 4) for x in itertools.product("ab", repeat=n)]
        for a, b in itertools.product(strings, repeat=2):
            found, distance = align_words(list(a), list(b))
            expected = paths(a, b)
            self.assertEqual(distance, expected[0][0])
            for i, row in enumerate(found):
                self.assertEqual(row["line_candidates"], sorted({mapping[i] for _, mapping in expected
                                                                if mapping[i] is not None}))
                self.assertEqual(row["whole_word_deletion_possible"], any(mapping[i] is None
                                                                          for _, mapping in expected))


if __name__ == "__main__":
    unittest.main()
