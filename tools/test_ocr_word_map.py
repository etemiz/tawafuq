import unittest
import itertools
from functools import lru_cache

from ocr_word_map import map_regions, map_mandatory_regions


def regions(*texts):
    return [dict(text=t, bbox=[100 * i, 0, 100 * i + 60, 40], bbox_valid=True)
            for i, t in enumerate(texts)]


class ExclusiveRegionsTest(unittest.TestCase):
    def test_spelling_error_keeps_region_identity(self):
        rows, cost = map_regions(["قال", "الله"], regions("قل", "الله"))
        self.assertEqual(cost, 1)
        self.assertEqual([r["exclusive_regions"] for r in rows], [[0], [1]])

    def test_multiword_region_never_gets_subdivided(self):
        rows, _ = map_regions(["قال", "الله"], regions("قال الله"))
        self.assertEqual([r["exclusive_regions"] for r in rows], [[], []])

    def test_repeated_word_deletion_retains_ambiguity(self):
        rows, _ = map_regions(["الله", "الله"], regions("الله"))
        self.assertTrue(all(r["whole_word_deletion_possible"] for r in rows))
        self.assertTrue(all(not r["exclusive_regions"] for r in rows))

    def test_split_prefix_uses_union_of_detected_geometry(self):
        rows, _ = map_regions(["والله"], regions("و", "الله"))
        self.assertEqual(rows[0]["region_candidates"], [0, 1])
        self.assertEqual(rows[0]["exclusive_regions"], [0, 1])
        self.assertEqual(rows[0]["bbox"], [0, 0, 160, 40])

    def test_cross_row_union_is_rejected(self):
        items = regions("و", "الله")
        items[1]["bbox"] = [0, 100, 60, 140]
        rows, _ = map_regions(["والله"], items)
        self.assertFalse(rows[0]["exclusive_regions"])

    def test_invalid_detector_box_is_rejected(self):
        items = regions("الله")
        items[0]["bbox_valid"] = False
        rows, _ = map_regions(["الله"], items)
        self.assertFalse(rows[0]["exclusive_regions"])


class MandatoryRegionsTest(unittest.TestCase):
    def test_mandatory_ownership_against_exhaustive_optimal_paths(self):
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

        strings = ["".join(chars) for n in range(1, 4) for chars in itertools.product("اب", repeat=n)]
        for reference, observed in itertools.product(strings, repeat=2):
            for ref_words in ([reference], list(reference)):
                owners = [i for i, word in enumerate(ref_words) for _ in word]
                for observed_regions in ([observed], list(observed)):
                    region_of = [i for i, text in enumerate(observed_regions) for _ in text]
                    optimal = paths(reference, observed)
                    expected = [[] for _ in ref_words]
                    for r in range(len(observed_regions)):
                        possible_owners = {owners[i] for _, mapping in optimal for i, j in enumerate(mapping)
                                           if j is not None and region_of[j] == r}
                        can_disappear = any(not any(j is not None and region_of[j] == r for j in mapping)
                                            for _, mapping in optimal)
                        if len(possible_owners) == 1 and not can_disappear:
                            expected[next(iter(possible_owners))].append(r)
                    found, cost = map_mandatory_regions(ref_words, regions(*observed_regions))
                    self.assertEqual(cost, optimal[0][0])
                    self.assertEqual([r["mandatory_regions"] for r in found], expected)

    def test_optional_inserted_fragment_does_not_widen_exact_word(self):
        items = regions("الله", "مه", "غفور")
        rows, _ = map_mandatory_regions(["الله", "غفور"], items)
        self.assertEqual(rows[0]["bbox"], items[0]["bbox"])
        self.assertEqual(rows[0]["mandatory_regions"], [0])

    def test_repeated_region_alternatives_are_not_treated_as_mandatory(self):
        rows, _ = map_mandatory_regions(["الله"], regions("الله", "الله"))
        self.assertFalse(rows[0]["exclusive_regions"])

    def test_true_split_prefix_has_mandatory_support(self):
        rows, _ = map_mandatory_regions(["والله"], regions("و", "الله"))
        self.assertEqual(rows[0]["exclusive_regions"], [0, 1])
        self.assertTrue(rows[0]["surface_match"])

    def test_detected_intervening_word_blocks_discontiguous_union(self):
        items = regions("و", "الله", "قال")
        items[0]["bbox"] = [0, 0, 30, 40]
        items[1]["bbox"] = [100, 0, 150, 40]
        items[2]["bbox"] = [50, 0, 80, 40]
        rows, _ = map_mandatory_regions(["والله", "قال"], items)
        self.assertFalse(rows[0]["exclusive_regions"])

    def test_multiword_region_does_not_certify_single_word(self):
        rows, _ = map_mandatory_regions(["قال", "الله"], regions("قال الله"))
        self.assertTrue(all(not r["exclusive_regions"] for r in rows))


if __name__ == "__main__":
    unittest.main()
