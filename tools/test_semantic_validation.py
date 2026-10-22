"""Small ground truths for corpus identity and localized validation."""
import unittest

import numpy as np
from PIL import Image

from semantic_validation import assess_pins, corpus_targets, independent_ink, selected_pages, STRATA, EXCLUDED


class SemanticValidationTests(unittest.TestCase):
    def test_exact_forms_ordinals_and_global_token_indices(self):
        verses = [(1, 1, ["بسم", "الله"]),
                  (2, 1, ["الله", "اللهو", "والله", "بالله"]),
                  (2, 2, ["لله", "يضلله", "ءالله"])]
        got = corpus_targets(verses, "2:1", "2:2")
        self.assertEqual([(x["verse"], x["occurrence"], x["form"], x["t"]) for x in got],
                         [("2:1", 1, "الله", 2), ("2:1", 2, "والله", 4),
                          ("2:1", 3, "بالله", 5), ("2:2", 1, "لله", 6),
                          ("2:2", 2, "ءالله", 8)])
        with self.assertRaises(ValueError):
            corpus_targets(verses, "2:2", "2:1")

    def test_token_identity_does_not_imply_correct_location(self):
        labels = {1: dict(page=5, rect=[10, 10, 30, 30]),
                  2: dict(page=5, rect=[50, 10, 70, 30])}
        pins = [dict(t=1, page=5, cx=20, cy=20),
                dict(t=2, page=5, cx=20, cy=20),
                dict(t=3, page=5, cx=60, cy=20),
                dict(t=1, page=6, cx=20, cy=20)]
        result = assess_pins(pins, labels)
        self.assertEqual(result["correct_localized_tokens"], 1)
        self.assertEqual(result["localized_token_recall"], 0.5)
        self.assertEqual(result["localized_prediction_precision"], 0.25)
        self.assertEqual(result["status_counts"],
                         dict(correct=1, wrong_position=1, wrong_page_or_token=2))

    def test_crop_pixels_distinguish_marking_from_no_detection(self):
        im = np.full((10, 10, 3), 255, dtype=np.uint8)
        im[4:6, 4:6] = [236, 43, 101]
        im[4, 6] = [209, 5, 125]
        image = Image.fromarray(im)
        measured = independent_ink(image, [2, 2, 8, 8])
        self.assertEqual(measured["colored_pixels"], 5)
        self.assertEqual(measured["crimson_pixels"], 4)
        self.assertEqual(measured["magenta_pixels"], 1)
        self.assertEqual(measured["ink_bbox"], [4, 4, 6, 5])
        self.assertEqual(independent_ink(image, [0, 0, 1, 1])["colored_pixels"], 0)

    def test_sample_keeps_each_stratum_and_excludes_training_anchors(self):
        pages = selected_pages()
        self.assertEqual(len(set(pages)), len(STRATA))
        for n, (lo, hi) in zip(pages, STRATA):
            self.assertTrue(lo <= n <= hi)
            self.assertNotIn(n, EXCLUDED)


if __name__ == "__main__":
    unittest.main()
