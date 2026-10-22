"""Independent finite-subset checks of geometric OCR alternative selection."""
import itertools
import random
import unittest

from ocr_observation_map import ObservationSpec, conflict, independent_set, observations


class ObservationTests(unittest.TestCase):
    def test_exact_graph_choice_against_all_subsets(self):
        rng = random.Random(26018)
        for n in range(1, 9):
            for _ in range(12):
                edges = [(i, j) for i in range(n) for j in range(i) if rng.random() < .4]
                weights = [rng.randrange(1, 20) for _ in range(n)]
                masks = [sum(1 << j for j in range(n) if (i, j) in edges or (j, i) in edges) for i in range(n)]
                valid = [tuple(i for i in range(n) if bits[i]) for bits in itertools.product((False, True), repeat=n)
                         if not any(bits[i] and bits[j] for i, j in edges)]
                chosen = min(valid, key=lambda ids: (-sum(weights[i] for i in ids), ids))
                self.assertEqual(independent_set(masks, weights), (sum(weights[i] for i in chosen), chosen))

    def test_split_and_combined_readings_are_not_both_text(self):
        regions = [dict(text=t, bbox=b, confidence=c, bbox_valid=True) for t, b, c in (
            ("والله", [100, 100, 200, 170], .95),
            ("و", [180, 100, 200, 170], .8),
            ("الله", [100, 100, 175, 170], .9),
            ("رب", [220, 100, 270, 170], .8))]
        result = observations(regions)
        self.assertEqual(result["retained"], [0, 3])
        self.assertEqual([r["source_region"] for r in result["removed"]], [1, 2])
        regions[0]["confidence"] = .5
        self.assertEqual(observations(regions)["retained"], [1, 2, 3])

    def test_filter_small_marks_before_ordering_and_keep_tall_prefixes(self):
        regions = [dict(text=t, bbox=b, confidence=1, bbox_valid=v) for t, b, v in (
            ("الله", [0, 100, 70, 180], True), ("ط", [80, 90, 95, 110], True),
            ("و", [100, 100, 115, 170], True), ("١٢", [130, 100, 160, 170], True),
            ("رب", [170, 100, 200, 170], False))]
        result = observations(regions)
        self.assertEqual(result["retained"], [0, 2])
        self.assertEqual([r["reason"] for r in result["removed"]],
                         ["small_observation", "nonlexical_observation", "invalid_box"])
        self.assertEqual(observations(regions, [(100, 181)])["retained"], [])

    def test_overlap_threshold_and_large_component_abstention(self):
        spec = ObservationSpec()
        self.assertTrue(conflict([0, 0, 100, 100], [40, 0, 140, 100], spec))
        self.assertFalse(conflict([0, 0, 100, 100], [41, 0, 141, 100], spec))
        regions = [dict(text="الله", bbox=[0, 0, 100, 100], confidence=.9)] * 3
        result = observations(regions, spec=ObservationSpec(maximum_component_size=2))
        self.assertEqual(result["retained"], [])
        self.assertEqual(result["overlap_components"][0]["status"], "size_limit_abstention")


if __name__ == "__main__":
    unittest.main()
