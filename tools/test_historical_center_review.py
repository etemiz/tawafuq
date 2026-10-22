"""Ground truths for paired coverage and strict, error-bounded phrase matches."""

from copy import deepcopy
from itertools import product
import unittest

from historical_center_review import phrase_bounds, validate


class HistoricalCenterReviewTests(unittest.TestCase):
    def rows(self, centers, row):
        return [dict(t=10*row+i, page=1, row=row, center=x,
                     frame_width=1000, word=word)
                for i, (x, word) in enumerate(zip(centers, ("من", "دون", "الله")))]

    def test_phrase_hull_agreement_does_not_certify_correspondence(self):
        first = self.rows([100, 200, 300], 1)
        second = self.rows([100, 250, 300], 2)
        result = phrase_bounds(first, second, .02, 0, 0)
        self.assertEqual(sum(w["midpoint_match"] for w in result["words"]), 2)
        self.assertFalse(result["midpoint_phrase_match"])

    def test_all_error_corners_respect_phrase_envelopes(self):
        first = self.rows([100, 200, 300], 1)
        second = self.rows([103, 216, 322], 2)
        result = phrase_bounds(first, second, .02, 5, 3)
        for offsets in product((-5, 5), repeat=6):
            for width in (994, 1006):
                matched = all(50*abs(first[i]["center"]+offsets[i]
                                    -second[i]["center"]-offsets[i+3]) <= width
                              for i in range(3))
                if result["guaranteed_phrase_match"]:
                    self.assertTrue(matched)
                if matched:
                    self.assertTrue(result["possible_phrase_match"])
        self.assertFalse(result["midpoint_phrase_match"])
        self.assertTrue(result["possible_phrase_match"])
        self.assertEqual([w["guaranteed"] for w in result["words"]], [True, False, False])

    def test_exact_inclusive_word_threshold_and_row_exclusion(self):
        first = self.rows([100, 200, 300], 1)
        second = self.rows([120, 220, 320], 2)
        self.assertTrue(phrase_bounds(first, second, .02, 0, 0)["midpoint_phrase_match"])
        second[1]["row"] = 1
        self.assertFalse(phrase_bounds(first, second, .02, 0, 0)["midpoint_phrase_match"])

    def test_identity_and_complete_word_coverage_required(self):
        first = self.rows([100, 200, 300], 1)
        second = self.rows([100, 200, 300], 2)
        with self.assertRaises(ValueError):
            phrase_bounds(first, second[:-1], .02)
        second[1]["word"] = "غير"
        with self.assertRaises(ValueError):
            phrase_bounds(first, second, .02)

    def test_paired_inventory_physical_page_and_nonverse_rows(self):
        selected = [dict(t=1, historical_page="50r", modern_page=97)]
        labels = dict(historical=[dict(page="50r", frame=[10,990],
                          row_end_anchors=["word"]*15, names=[[1,2,100,150]])],
                      modern=[dict(page=97, frame=[10,990], names=[[1,5,200,250]])])
        validate(labels, selected)
        for change in ("missing", "duplicate", "wrong_page", "outside", "nonverse"):
            broken = deepcopy(labels)
            if change == "missing":
                broken["modern"][0]["names"] = []
            elif change == "duplicate":
                broken["modern"][0]["names"] *= 2
            elif change == "wrong_page":
                broken["modern"][0]["page"] = 98
            elif change == "outside":
                broken["modern"][0]["names"][0][2] = 0
            else:
                broken["historical"][0]["nonverse_rows"] = {"2": "heading"}
                broken["historical"][0]["row_end_anchors"][1] = None
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate(broken, selected)


if __name__ == "__main__":
    unittest.main()
