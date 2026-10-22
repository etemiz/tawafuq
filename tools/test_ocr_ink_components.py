"""Independent exhaustive oracle and topology counterexamples."""
import itertools
import unittest

import numpy as np
from PIL import Image

from ocr_ink_components import index_components, component_records, summarize, measure


class InkComponentTests(unittest.TestCase):
    def test_diagonal_contact_distinguishes_four_and_eight(self):
        mask = np.eye(3, dtype=bool)
        for connectivity, expected in ((4, 3), (8, 1)):
            rows = component_records(index_components(mask, connectivity), [0, 0, 3, 3], mask)
            self.assertEqual(len(rows), expected)

    def test_oracle_matches_every_component_assignment_for_every_tiny_partition(self):
        for states in itertools.product(range(3), repeat=6):
            mask = np.array([s > 0 for s in states]).reshape(2, 3)
            truth = np.array([s == 1 for s in states]).reshape(2, 3)
            for connectivity in (4, 8):
                index = index_components(mask, connectivity)
                rows = component_records(index, [0, 0, 3, 2], truth)
                errors = []
                for choices in itertools.product((False, True), repeat=len(rows)):
                    selected = [row["component_id"] for row, yes in zip(rows, choices) if yes]
                    predicted = np.isin(index[0], selected)
                    errors.append(int(np.count_nonzero(predicted != truth)))
                summary = summarize(rows, True)
                self.assertEqual(summary["oracle_minimum_pixel_errors"], min(errors))
                self.assertEqual(summary["exact_in_box_partition_representable"], min(errors) == 0)

    def test_outside_crop_bridge_couples_target_and_foreign_ink(self):
        image = Image.new("RGB", (5, 5), "white")
        for point in ((1, 1), (1, 2), (1, 3), (2, 3), (3, 3), (3, 2), (3, 1)):
            image.putpixel(point, (0, 0, 0))
        reference = dict(partition=[1, 0, 2, 5], ink_class="black", in_box_projection=dict(ink_pixels=2))
        result = measure(image, [0, 0, 5, 3], reference)
        for connectivity in (4, 8):
            self.assertEqual(result[f"crop_{connectivity}"]["summary"]["oracle_minimum_pixel_errors"], 0)
            self.assertEqual(result[f"page_{connectivity}"]["summary"]["oracle_minimum_pixel_errors"], 2)
            self.assertEqual(result[f"page_{connectivity}"]["components"][0]["outside_box_ink_pixels"], 3)

    def test_color_contact_can_mix_target_and_foreign_ink(self):
        image = Image.new("RGB", (4, 3), "white")
        image.putpixel((1, 1), (200, 0, 80))
        image.putpixel((2, 1), (0, 0, 0))
        reference = dict(partition=[1, 0, 2, 3], ink_class="colored", in_box_projection=dict(ink_pixels=1))
        result = measure(image, [0, 0, 4, 3], reference)
        self.assertEqual(result["page_8"]["summary"]["oracle_minimum_pixel_errors"], 1)
        self.assertEqual(result["page_8"]["summary"]["mixed_components"], 1)

    def test_no_reference_has_no_oracle_and_empty_ink_has_no_components(self):
        result = measure(Image.new("RGB", (3, 3), "white"), [0, 0, 3, 3])
        for row in result.values():
            self.assertEqual(row["components"], [])
            self.assertNotIn("oracle_minimum_pixel_errors", row["summary"])


if __name__ == "__main__":
    unittest.main()
