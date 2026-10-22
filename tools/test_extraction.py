"""Small pixel ground truths, not copies of the labeling implementation."""
import unittest
import numpy as np

from page_scan import components, dilate
from divine_census import norm, TRUE_FORMS, corpus_counts
import map_tokens
from PIL import Image
from image_io import on_white
from red_clusters import kmeans
from rosette_digits import extract_page_gold
from find_basmala import candidate_bands


class ExtractionTests(unittest.TestCase):
    def test_magenta_basmala_stroke_need_not_fill_fifteen_rows(self):
        image = np.full((160, 600, 3), 255, dtype=np.int16)
        image[40:83, 100:120] = [210, 5, 125]
        image[80:83, 100:450] = [210, 5, 125]
        self.assertEqual(candidate_bands(image, [(0, 150)]), [(40, 83, 350)])
        self.assertEqual(candidate_bands(image, [(100, 150)]), [])

    def test_first_line_rosette_keeps_small_zero_digit(self):
        # A gold-bordered pale number panel with a stroke and a 3x3 zero
        # dot. Ground truth: two digits, above the old y=110 cutoff.
        im = np.full((55, 65, 3), 255, dtype=np.int16)
        im[20:46, 10:52] = [170, 160, 30]
        im[25:41, 17:45] = [210, 240, 230]
        im[29:37, 23:26] = [20, 20, 20]
        im[33:36, 34:37] = [20, 20, 20]
        rosettes = extract_page_gold(im)
        self.assertEqual(len(rosettes), 1)
        self.assertEqual(rosettes[0]["ndig"], 2)
        self.assertIn(9, rosettes[0]["dsizes"])
        self.assertEqual(extract_page_gold(im, min_digit_pixels=10)[0]["ndig"], 1)

    def test_alpha_is_paper_not_black_ink(self):
        im = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
        im.putpixel((1, 0), (236, 43, 101, 255))
        self.assertEqual(np.asarray(on_white(im)).tolist(), [[[255, 255, 255], [236, 43, 101]]])

    def test_memory_bounded_kmeans_agrees_with_direct_distances(self):
        x = np.random.default_rng(8).normal(size=(40, 5))
        rng = np.random.default_rng(5)
        centers = x[rng.choice(len(x), 3, replace=False)].copy()
        for _ in range(10):
            labels = ((x[:, None] - centers[None]) ** 2).sum(axis=2).argmin(axis=1)
            for k in range(3):
                if (labels == k).any():
                    centers[k] = x[labels == k].mean(axis=0)
        expected = ((x[:, None] - centers[None]) ** 2).sum(axis=2).argmin(axis=1)
        labels, got = kmeans(x, 3, iters=10, seed=5)
        np.testing.assert_array_equal(labels, expected)
        np.testing.assert_allclose(got, centers)

    def test_last_isolated_component_not_lost(self):
        mask = np.zeros((5, 5), dtype=bool)
        mask[1, 1] = mask[3, 3] = True
        a = np.zeros((5, 5, 3), dtype=np.uint8)
        got = components(a, mask, mask, min_px=1)
        self.assertEqual([(c["x0"], c["y0"], c["npx"]) for c in got], [(1, 1, 1), (3, 3, 1)])

    def test_bridged_labels_are_one_region(self):
        mask = np.array([[1, 0, 1], [1, 1, 1]], dtype=bool)
        got = components(np.zeros((2, 3, 3), dtype=np.uint8), mask, mask, min_px=1)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["npx"], 5)

    def test_color_ignores_other_region_inside_box(self):
        mask = np.zeros((7, 7), dtype=bool)
        mask[0, :] = mask[-1, :] = mask[:, 0] = mask[:, -1] = True
        mask[2:5, 2:5] = True
        a = np.zeros((7, 7, 3), dtype=np.uint8)
        a[2:5, 2:5] = [200, 0, 0]
        got = components(a, mask, mask, min_px=1)
        self.assertEqual({c["med"] for c in got}, {(0, 0, 0), (200, 0, 0)})

    def test_dilation_does_not_wrap(self):
        mask = np.zeros((7, 7), dtype=bool)
        mask[0, 0] = True
        got = dilate(mask, 1)
        self.assertEqual(set(zip(*np.where(got))), {(0, 0), (1, 0), (0, 1)})

    def test_interrogative_name_and_basmala_accounting(self):
        self.assertEqual(norm("ءَآللَّهُ"), "ءالله")
        self.assertIn("ءالله", TRUE_FORMS)
        c, n = corpus_counts()
        self.assertEqual(c["ءالله"], 2)
        self.assertEqual(n, 1)
        total = sum(v for k, v in c.items() if not k.startswith("FALSE:"))
        self.assertEqual(total + n, 2699)
        self.assertEqual(total + n + 112, 2811)

    def test_width_model_is_loaded_from_actual_schema(self):
        model_value = map_tokens.est_width("الله")
        self.assertIsNotNone(map_tokens.est_width.model)
        self.assertAlmostEqual(model_value, 31.69 + 8.63 + 2 * 8.42 + 8.88)


if __name__ == "__main__":
    unittest.main()
