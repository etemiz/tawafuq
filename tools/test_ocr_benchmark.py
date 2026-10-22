"""Independent edit-distance and Arabic normalization ground truths."""
import itertools
import unittest
from functools import lru_cache

from ocr_benchmark import edit_counts, reading_order, words


class OCRBenchmarkTests(unittest.TestCase):
    def test_edit_distance_against_recursive_all_tiny_strings(self):
        @lru_cache(None)
        def distance(a, b):
            if not a or not b:
                return len(a) + len(b)
            return min(distance(a[1:], b) + 1, distance(a, b[1:]) + 1,
                       distance(a[1:], b[1:]) + (a[0] != b[0]))
        strings = ["".join(x) for n in range(4) for x in itertools.product("ab", repeat=n)]
        for a, b in itertools.product(strings, repeat=2):
            result = edit_counts(a, b)
            self.assertEqual(result["distance"], distance(a, b))
            self.assertEqual(result["distance"], sum(result[k] for k in
                                                   ("substitutions", "deletions", "insertions")))

    def test_arabic_diacritics_and_digits_without_silent_word_correction(self):
        self.assertEqual(words("وَٱللَّهُ ١٠٢ بِـٱللَّهِ ۞ الرَّحْمَةُ"), ["والله", "بالله", "الرحمه"])
        self.assertEqual(words("وَ اللَّهُ"), ["و", "الله"])

    def test_same_row_fragments_read_right_to_left(self):
        left = dict(text="left", bbox=[10, 10, 50, 30])
        right = dict(text="right", bbox=[60, 12, 100, 32])
        below = dict(text="below", bbox=[10, 100, 100, 120])
        self.assertEqual([x["text"] for x in reading_order([below, left, right])],
                         ["right", "left", "below"])


if __name__ == "__main__":
    unittest.main()
