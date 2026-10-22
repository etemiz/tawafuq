import unittest

from word_localization_validation import assess


class LocalizationAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.label = dict(rect=[100, 200, 180, 270], x_edges=[100, 180], x_edge_tolerance=12)

    def test_center_success_does_not_certify_boundary(self):
        result = assess(dict(bbox=[50, 200, 230, 270]), self.label)
        self.assertTrue(result["center_correct"])
        self.assertFalse(result["horizontal_boundary_pass"])

    def test_correct_edges_on_wrong_row_fail(self):
        result = assess(dict(bbox=[100, 300, 180, 370]), self.label)
        self.assertFalse(result["correct_line"])
        self.assertFalse(result["horizontal_boundary_pass"])

    def test_abstention_remains_in_denominator(self):
        result = assess({}, self.label)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["center_correct"])

    def test_boundary_tolerance_includes_endpoints(self):
        self.assertTrue(assess(dict(bbox=[88, 200, 192, 270]), self.label)["horizontal_boundary_pass"])
        self.assertFalse(assess(dict(bbox=[87, 200, 192, 270]), self.label)["horizontal_boundary_pass"])

    def test_ambiguous_partition_cannot_pass_boundary_check(self):
        self.label["boundary_eligible"] = False
        result = assess(dict(bbox=[100, 200, 180, 270]), self.label)
        self.assertTrue(result["center_correct"])
        self.assertFalse(result["horizontal_boundary_pass"])


if __name__ == "__main__":
    unittest.main()
