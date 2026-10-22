"""Independent exhaustive ownership-subset checks for horizontal edge ranges."""
import itertools
import unittest

import numpy as np
from PIL import Image

from word_boundary_extent_review import ownership_bounds, measure_extent, inventory


class ExtentReviewTests(unittest.TestCase):
    def test_all_small_masks_and_every_optional_pixel_subset(self):
        for states in itertools.product(range(3), repeat=6):
            mandatory = np.array([s == 1 for s in states]).reshape(2, 3)
            if not mandatory.any():
                continue
            possible = np.array([s != 0 for s in states]).reshape(2, 3)
            optional = [i for i, s in enumerate(states) if s == 2]
            edges = []
            for choices in itertools.product((False, True), repeat=len(optional)):
                mask = mandatory.copy().reshape(-1)
                for i, included in zip(optional, choices):
                    mask[i] = included
                columns = [i % 3 for i, included in enumerate(mask) if included]
                edges.append((7+min(columns), 8+max(columns)))
            result = ownership_bounds(mandatory, possible, 7)
            expected = [[min(e[k] for e in edges), max(e[k] for e in edges)] for k in (0, 1)]
            self.assertEqual(result["x_edge_ranges"], expected, states)
            self.assertEqual(result["horizontal_invariant"], len(set(edges)) == 1, states)
            self.assertEqual(result["optional_ink_pixels"], len(optional))

    def test_optional_colored_ink_can_be_interior_or_change_an_edge(self):
        image = Image.new("RGB", (7, 3), "white")
        image.putpixel((2, 1), (10, 10, 10))
        image.putpixel((4, 1), (10, 10, 10))
        image.putpixel((3, 0), (230, 0, 100))
        label = dict(partition=[0, 0, 7, 3], ink_class="mixed", optional_colored=True)
        pixels, bounds = measure_extent(image, label)
        self.assertEqual(pixels["ink_pixels"], 3)
        self.assertEqual(bounds["x_edge_ranges"], [[2, 2], [5, 5]])
        self.assertTrue(bounds["horizontal_invariant"])
        image.putpixel((6, 1), (230, 0, 100))
        pixels, bounds = measure_extent(image, label)
        self.assertEqual(bounds["x_edge_ranges"], [[2, 2], [5, 7]])
        self.assertFalse(bounds["horizontal_invariant"])
        self.assertTrue(pixels["horizontal_partition_contact"])

    def test_invalid_or_empty_mandatory_ink_cannot_certify_edges(self):
        for mandatory, possible in (([[True]], [[False]]), ([[False]], [[True]]),
                                    ([[True]], [[True, True]]), ([True], [True])):
            with self.assertRaises(AssertionError):
                ownership_bounds(mandatory, possible)
        image = Image.new("RGB", (3, 3), "black")
        with self.assertRaises(AssertionError):
            measure_extent(image, dict(partition=[0, 0, 3, 3], ink_class="black", optional_colored=True))
        with self.assertRaises(AssertionError):
            measure_extent(image, dict(partition=[0, 0, 3, 3], ink_class="black", optional_rects=[[-1, 0, 1, 1]]))

    def test_inventory_is_all_unscorable_words_but_never_unavailable_slots(self):
        report = dict(pages=[dict(page=5, word_samples=[
            dict(status="unavailable"), dict(boundary_eligible=True, t=1), dict(boundary_eligible=False, t=2)])])
        self.assertEqual(inventory(report), [(5, dict(boundary_eligible=False, t=2))])


if __name__ == "__main__":
    unittest.main()
