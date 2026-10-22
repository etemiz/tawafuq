"""Independent finite-image checks for in-box ink-hull properties and limits."""
import itertools
import unittest

from PIL import Image

from ocr_ink_trim import measure, trim
from word_boundary_ink_audit import outcome


class InkTrimTests(unittest.TestCase):
    def test_every_small_mask_minimality_containment_and_ink_preservation(self):
        box = [2, 3, 5, 5]
        for values in itertools.product((False, True), repeat=6):
            image = Image.new("RGB", (7, 7), "white")
            points = [(2+i % 3, 3+i//3) for i, ink in enumerate(values) if ink]
            for point in points:
                image.putpixel(point, (0, 0, 0))
            result = trim(box, measure(image, box))
            candidate = result["bbox"]
            self.assertEqual(candidate[1::2], box[1::2])
            self.assertTrue(box[0] <= candidate[0] < candidate[2] <= box[2])
            for x, y in points:
                self.assertTrue(candidate[0] <= x < candidate[2] and candidate[1] <= y < candidate[3])
            if points:
                xs = [x for x, _ in points]
                self.assertEqual(candidate[::2], [min(xs), max(xs)+1])
                self.assertEqual(result["ink_pixels"], len(points))
                # Any strictly narrower horizontal interval must omit ink.
                for left in range(candidate[0], candidate[2]):
                    for right in range(left+1, candidate[2]+1):
                        if (left, right) != (candidate[0], candidate[2]):
                            self.assertTrue(any(not left <= x < right for x, _ in points))
            else:
                self.assertEqual(candidate, box)
                self.assertEqual(result["status"], "no_threshold_ink")

    def test_colored_letters_are_ink_and_outside_pixels_are_never_read(self):
        image = Image.new("RGB", (10, 7), "white")
        image.putpixel((1, 3), (0, 0, 0))
        image.putpixel((4, 3), (225, 0, 100))
        image.putpixel((6, 4), (225, 0, 100))
        self.assertEqual(trim([3, 2, 8, 6], measure(image, [3, 2, 8, 6]))["bbox"], [4, 2, 7, 6])

    def test_exact_thresholds_and_int16_channel_subtraction(self):
        image = Image.new("RGB", (7, 2), "white")
        for x, color in enumerate(((119, 119, 119), (120, 120, 120), (121, 75, 200),
                                   (121, 76, 200), (0, 255, 0), (120, 0, 0), (121, 0, 0))):
            image.putpixel((x, 0), color)
        pixels = measure(image, [0, 0, 7, 2])
        self.assertEqual(pixels["column_ink_counts"], [1, 0, 1, 0, 0, 0, 1])

    def test_trimming_can_move_a_previously_correct_center_outside_its_core(self):
        image = Image.new("RGB", (12, 5), "white")
        image.putpixel((9, 2), (0, 0, 0))
        box = [0, 0, 10, 5]
        candidate = trim(box, measure(image, box))["bbox"]
        label = dict(rect=[4, 0, 6, 5])
        self.assertTrue(outcome(box, label, None)["center_correct"])
        self.assertFalse(outcome(candidate, label, None)["center_correct"])

    def test_uncertain_edges_abstentions_and_unavailable_stay_explicit(self):
        label = dict(rect=[495, 0, 610, 10], x_edges=[506, 607],
                     x_edge_tolerance=12, boundary_eligible=False)
        result = outcome([497, 0, 600, 10], label, [[506], [597, 607]])
        self.assertFalse(result["horizontal_boundary_pass"])
        self.assertTrue(result["all_ownership_boundary_pass"])
        self.assertFalse(outcome(None, label, [[506], [597, 607]])["accepted"])
        self.assertFalse(outcome(None, label, [[506], [597, 607]])["all_ownership_boundary_pass"])
        self.assertEqual(outcome(None, dict(status="unavailable"), None), dict(status="unavailable"))

    def test_missing_letters_and_neighboring_ink_cannot_be_repaired(self):
        image = Image.new("RGB", (12, 5), "white")
        for point in ((1, 2), (5, 2), (8, 2), (11, 2)):
            image.putpixel(point, (0, 0, 0))
        box = [3, 0, 10, 5]
        candidate = trim(box, measure(image, box))["bbox"]
        self.assertEqual(candidate, [5, 0, 9, 5])
        # Missing canonical ink at x11 remains missing; neighbor at x5 stays.
        self.assertFalse(candidate[0] <= 11 < candidate[2])
        self.assertTrue(candidate[0] <= 5 < candidate[2])

    def test_invalid_boxes_and_projection_counts(self):
        image = Image.new("RGB", (4, 4), "white")
        for box in ((0, 0, 0, 2), (-1, 0, 2, 2), (0, 0, 5, 2), (0, 0, 2.0, 2), (False, 0, 2, 2)):
            with self.assertRaises(AssertionError):
                measure(image, box)
        for pixels in (dict(column_ink_counts=[1, 0], row_ink_counts=[0, 0]),
                       dict(column_ink_counts=[3, 0], row_ink_counts=[2, 1]),
                       dict(column_ink_counts=[1], row_ink_counts=[1, 0])):
            with self.assertRaises(AssertionError):
                trim([0, 0, 2, 2], pixels)


if __name__ == "__main__":
    unittest.main()
