"""Independent finite-set oracle and geometric failure tests for evidence masks."""
import itertools
import unittest

import numpy as np
from PIL import Image

from ocr_ownership_evidence import overlaps, rosette_box, rectangle_mask, project, proposal, measure, reference_checks
from word_ownership_evidence_audit import regressions


class OwnershipEvidenceTests(unittest.TestCase):
    def test_every_small_mask_subset_and_joint_edge_support(self):
        box = [7, 3, 10, 5]
        for states in itertools.product(range(3), repeat=6):
            m = np.array([s == 1 for s in states]).reshape(2, 3)
            p = np.array([s != 0 for s in states]).reshape(2, 3)
            result = proposal(box, project(p), project(m))
            if not m.any():
                self.assertIsNone(result["conditional_edge_support"])
                self.assertEqual(result["bbox"], box)
                continue
            optional = [i for i, s in enumerate(states) if s == 2]
            edges = set()
            for choice in itertools.product((False, True), repeat=len(optional)):
                columns = [i % 3+7 for i, s in enumerate(states) if s == 1]
                columns += [i % 3+7 for i, yes in zip(optional, choice) if yes]
                edges.add((min(columns), max(columns)+1))
            self.assertEqual(set(itertools.product(*result["conditional_edge_support"])), edges)
            self.assertEqual(result["horizontal_invariant"], len(edges) == 1)
            own_columns = [i % 3+7 for i, s in enumerate(states) if s == 1]
            self.assertEqual(result["bbox"], [min(own_columns), 3, max(own_columns)+1, 5])

    def test_half_open_rectangle_intersection_and_column_shadow(self):
        box = [2, 3, 7, 7]
        marker = [0, 4, 4, 6]
        local = rectangle_mask(box, [marker])
        shadow = rectangle_mask(box, [marker], columns=True)
        self.assertEqual(int(local.sum()), 4)
        self.assertEqual(int(shadow.sum()), 8)
        self.assertFalse(overlaps(box, [7, 3, 9, 7]))
        self.assertFalse(rectangle_mask(box, [[7, 3, 9, 7]], columns=True).any())
        self.assertEqual(rosette_box(dict(cx=4.5, cy=5, w=5, h=4)), [2, 3, 7, 7])

    def test_unclaimed_foreign_letter_survives_other_word_subtraction(self):
        image = Image.new("RGB", (12, 5), "white")
        for point in ((3, 2), (7, 2), (9, 2)):
            image.putpixel(point, (0, 0, 0))
        box = [2, 0, 11, 5]
        measured = measure(image, box, [[0, 0, 2, 5]], [])
        result = proposal(box, measured["possible"], measured["policies"]["other_words"])
        self.assertEqual(result["bbox"], [3, 0, 10, 5])
        self.assertTrue(result["horizontal_invariant"])
        # Invariance is true but the foreign pixel at x3 was never claimed.
        self.assertEqual(result["optional_ink_pixels"], 0)

    def test_marker_shadow_can_fix_margin_while_clipping_real_target_ink(self):
        image = Image.new("RGB", (12, 8), "white")
        for point in ((3, 3), (3, 1), (5, 1), (7, 4), (9, 4)):
            image.putpixel(point, (0, 0, 0))
        box = [2, 0, 11, 7]
        truth = dict(partition=[5, 0, 11, 7], ink_class="black", pixels=dict(ink_pixels=3))
        measured = measure(image, box, [], [[2, 2, 6, 5]], truth)
        rect = proposal(box, measured["possible"], measured["policies"]["rosette_rectangles"])
        shadow = proposal(box, measured["possible"], measured["policies"]["rosette_columns_stress"])
        self.assertEqual(rect["bbox"][0], 3)  # The stop sign above the marker stays.
        self.assertEqual(shadow["bbox"][0], 7)
        reference = reference_checks(box, shadow["bbox"], measured["possible"],
                                     measured["policies"]["rosette_columns_stress"], measured["clear_manual_reference"])
        self.assertEqual(reference["extra_target_pixels_clipped"], 1)
        self.assertEqual(reference["target_pixels_made_optional"], 1)

    def test_empty_mandatory_does_not_certify_an_edge_or_delete_the_box(self):
        image = Image.new("RGB", (4, 4), "black")
        measured = measure(image, [0, 0, 4, 4], [[0, 0, 4, 4]], [])
        result = proposal([0, 0, 4, 4], measured["possible"], measured["policies"]["other_words"])
        self.assertEqual(result["status"], "empty_mandatory_fallback")
        self.assertIsNone(result["conditional_edge_support"])
        self.assertEqual(result["bbox"], [0, 0, 4, 4])

    def test_missing_outside_target_ink_is_counted_and_never_recovered(self):
        image = Image.new("RGB", (8, 4), "white")
        for point in ((3, 2), (5, 2), (7, 2)):
            image.putpixel(point, (200, 0, 80))
        box = [2, 0, 6, 4]
        truth = dict(partition=[2, 0, 8, 4], ink_class="colored", pixels=dict(ink_pixels=3))
        measured = measure(image, box, [], [], truth)
        policy = measured["policies"]["other_words"]
        proposed = proposal(box, measured["possible"], policy)
        reference = reference_checks(box, proposed["bbox"], measured["possible"], policy, measured["clear_manual_reference"])
        self.assertEqual(reference["target_pixels_outside_original_box"], 1)
        self.assertEqual(reference["target_pixels_outside_candidate_box"], 1)
        self.assertEqual(reference["extra_target_pixels_clipped"], 0)

    def test_invalid_projection_cannot_supply_bounds(self):
        p = project(np.ones((2, 3), bool))
        for m in (dict(column_ink_counts=[3, 0, 0], ink_pixels=3),
                  dict(column_ink_counts=[1, 0], ink_pixels=1),
                  dict(column_ink_counts=[1, 0, 0], ink_pixels=2)):
            with self.assertRaises(AssertionError):
                proposal([0, 0, 3, 2], p, m)

    def test_a_preexisting_boundary_failure_cannot_hide_a_new_center_regression(self):
        row = dict(boundary_eligible=True, ownership_evaluable=False,
                   baseline=dict(status="correct_center", center_correct=True, horizontal_boundary_pass=False),
                   candidate=dict(status="wrong_center", center_correct=False, horizontal_boundary_pass=False))
        self.assertEqual(regressions(row), ["center"])


if __name__ == "__main__":
    unittest.main()
