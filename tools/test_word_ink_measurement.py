import unittest

from PIL import Image, ImageDraw

from adjudicate_word_sample import measure


class IndependentWordInkTests(unittest.TestCase):
    def setUp(self):
        self.image = Image.new("RGB", (40, 20), "white")
        draw = ImageDraw.Draw(self.image)
        draw.rectangle([10, 5, 16, 10], fill=(30, 30, 30))
        draw.rectangle([22, 4, 26, 11], fill=(236, 43, 101))

    def test_black_edges_exclude_colored_neighbor_and_preserve_offset(self):
        result = measure(self.image, [5, 0, 30, 20], "black")
        self.assertEqual(result["ink_bbox"], [10, 5, 17, 11])
        self.assertEqual(result["ink_pixels"], 42)
        self.assertFalse(result["horizontal_partition_contact"])

    def test_color_edges_exclude_black_neighbor(self):
        result = measure(self.image, [5, 0, 30, 20], "crimson")
        self.assertEqual(result["ink_bbox"], [22, 4, 27, 12])

    def test_ink_contact_marks_boundary_uncertain(self):
        result = measure(self.image, [10, 0, 30, 20], "black")
        self.assertTrue(result["horizontal_partition_contact"])


if __name__ == "__main__":
    unittest.main()
