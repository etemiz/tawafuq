"""Guard unavailable/abstained denominators and the mixed-ink pixel extension."""
import unittest

from PIL import Image

from word_boundary_fresh_sample import measure_ink
from word_boundary_fresh_validation import summarize


class FreshV5ValidationTests(unittest.TestCase):
    def test_unavailable_is_not_abstained_and_abstained_boundary_stays_in_denominator(self):
        details = [
            dict(status="correct_center", accepted=True, center_correct=True,
                 boundary_eligible=True, horizontal_boundary_pass=True),
            dict(status="wrong_center", accepted=True, center_correct=False,
                 boundary_eligible=False, horizontal_boundary_pass=False),
            dict(status="abstained", accepted=False, center_correct=False,
                 boundary_eligible=True, horizontal_boundary_pass=False),
            dict(status="unavailable", reason="No seventh word on this row"),
        ]
        self.assertEqual(summarize(details), dict(scheduled=4, labelled=3, unavailable=1, accepted=2,
            correct_centers=1, wrong_accepted=1, abstentions=1, boundary_evaluable=2, boundary_pass=1))

    def test_mixed_word_keeps_both_inks_but_not_gold_or_background(self):
        image = Image.new("RGB", (5, 3), "white")
        image.putpixel((1, 1), (20, 20, 20))
        image.putpixel((3, 1), (230, 0, 90))
        image.putpixel((0, 0), (150, 135, 20))
        mixed = measure_ink(image, (0, 0, 5, 3), "mixed")
        self.assertEqual(mixed["ink_pixels"], 2)
        self.assertEqual(mixed["ink_bbox"], [1, 1, 4, 2])
        self.assertFalse(mixed["horizontal_partition_contact"])
        self.assertEqual(measure_ink(image, (0, 0, 5, 3), "black")["ink_bbox"], [1, 1, 2, 2])
        self.assertEqual(measure_ink(image, (0, 0, 5, 3), "colored")["ink_bbox"], [3, 1, 4, 2])
        self.assertTrue(measure_ink(image, (1, 0, 4, 3), "mixed")["horizontal_partition_contact"])

    def test_empty_partition_or_unspecified_ink_cannot_create_a_boundary(self):
        image = Image.new("RGB", (2, 2), "white")
        for ink in ("mixed", "not-an-ink-class"):
            with self.assertRaises(AssertionError):
                measure_ink(image, (0, 0, 2, 2), ink)


if __name__ == "__main__":
    unittest.main()
