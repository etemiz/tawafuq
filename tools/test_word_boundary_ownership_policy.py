"""Independent finite-mask oracle for exact ownership-policy scoring."""
import itertools
import unittest

import numpy as np
from PIL import Image

from word_boundary_ownership_policy import edge_support, score_support, assess_policy, measure_support


class OwnershipPolicyTests(unittest.TestCase):
    def test_exhaustive_masks_joint_support_and_error_extrema(self):
        for states in itertools.product(range(3), repeat=6):
            mandatory = np.array([s == 1 for s in states]).reshape(2, 3)
            if not mandatory.any():
                continue
            possible = np.array([s != 0 for s in states]).reshape(2, 3)
            optional = [i for i, s in enumerate(states) if s == 2]
            edges = set()
            for choices in itertools.product((False, True), repeat=len(optional)):
                columns = [i % 3+7 for i, s in enumerate(states) if s == 1]
                columns += [i % 3+7 for i, yes in zip(optional, choices) if yes]
                edges.add((min(columns), max(columns)+1))
            support = edge_support(mandatory, possible, 7)
            self.assertEqual(set(itertools.product(*support)), edges, states)
            for predicted in ((6, 10), (8, 9), (9, 11)):
                errors = [max(abs(p-t) for p, t in zip(predicted, pair)) for pair in edges]
                for tolerance in (0, 1, 2):
                    result = score_support(predicted, support, tolerance)
                    self.assertEqual(result["best_max_abs_error"], min(errors))
                    self.assertEqual(result["worst_max_abs_error"], max(errors))
                    expected = ("all_pass" if all(e <= tolerance for e in errors) else
                                "all_fail" if all(e > tolerance for e in errors) else "ownership_sensitive")
                    self.assertEqual(result["ownership_outcome"], expected)

    def test_holes_cannot_be_filled_by_interval_interpolation(self):
        # Optional ink at x0, mandatory ink at x2: L=1 is impossible.
        support = edge_support([[False, False, True]], [[True, False, True]])
        self.assertEqual(support, [[0, 2], [3]])
        result = score_support([1, 3], support, 0)
        self.assertEqual(result["ownership_outcome"], "all_fail")
        self.assertEqual(result["best_max_abs_error"], 1)

    def test_two_endpoint_policies_can_fail_while_an_interior_mask_passes(self):
        support = [[0, 1, 2], [5, 6, 7]]
        row = dict(accepted=True, correct_line=True, bbox=[1, 0, 6, 1], x_edge_tolerance=0)
        result = assess_policy(row, support)
        self.assertFalse(result["mandatory_only_pass"])
        self.assertFalse(result["include_optional_pass"])
        self.assertEqual(result["status"], "ownership_sensitive")
        self.assertEqual(result["best_max_abs_error"], 0)

    def test_tolerance_equality_abstention_line_and_unavailable(self):
        row = dict(accepted=True, correct_line=True, bbox=[497, 0, 600, 1], x_edge_tolerance=12)
        self.assertTrue(assess_policy(row, [[506], [597, 607]])["all_ownership_pass"])
        self.assertEqual(score_support([0, 10], [[12], [22]], 12)["ownership_outcome"], "all_pass")
        self.assertFalse(assess_policy(dict(row, accepted=False), [[506], [597, 607]])["all_ownership_pass"])
        self.assertFalse(assess_policy(dict(row, correct_line=False), [[506], [597, 607]])["all_ownership_pass"])
        self.assertEqual(assess_policy(dict(status="unavailable"), None), dict(status="unavailable"))
        self.assertIsNone(assess_policy(row, None)["all_ownership_pass"])

    def test_colored_lexical_ink_is_mandatory_unless_explicitly_optional(self):
        image = Image.new("RGB", (8, 4), "white")
        image.putpixel((2, 1), (220, 0, 100))
        image.putpixel((6, 2), (220, 0, 100))
        label = dict(partition=[0, 0, 8, 4], ink_class="colored")
        self.assertEqual(measure_support(image, label), [[2], [7]])
        image.putpixel((3, 2), (10, 10, 10))
        label.update(ink_class="mixed", optional_colored=True)
        self.assertEqual(measure_support(image, label), [[2, 3], [4, 7]])
        label.pop("optional_colored")
        label["optional_rects"] = [[6, 2, 7, 3]]
        self.assertEqual(measure_support(image, label), [[2], [4, 7]])

    def test_invalid_support_and_masks(self):
        for mandatory, possible in (([[False]], [[True]]), ([[True]], [[False]]),
                                    ([True], [True]), ([[True]], [[True, False]])):
            with self.assertRaises(AssertionError):
                edge_support(mandatory, possible)
        for support in (([], [4]), ([3], [3]), ([2, 1], [4]), ([1, 1], [4])):
            with self.assertRaises(AssertionError):
                score_support([1, 4], support, 12)


if __name__ == "__main__":
    unittest.main()
