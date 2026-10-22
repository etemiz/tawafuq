import unittest

from ocr_corpus_sites import site


class WordlikeSiteTests(unittest.TestCase):
    def test_single_region_uses_own_box_despite_other_box_overlap(self):
        regions = [dict(text="الله", bbox=[230, 250, 360, 328], bbox_valid=True),
                   dict(text="م", bbox=[320, 257, 345, 328], bbox_valid=True)]
        row, status = site(dict(mandatory_regions=[0], normalized="الله"), regions)
        self.assertEqual(status, "single_mandatory_region_no_union")
        self.assertEqual(row["bbox"], regions[0]["bbox"])

    def test_rejected_union_is_not_silently_rescued(self):
        row, status = site(dict(mandatory_regions=[0, 1], normalized="والله"), [])
        self.assertIsNone(row)
        self.assertEqual(status, "no_usable_support")

    def test_tiny_exact_ocr_match_remains_excluded_as_a_wordlike_site(self):
        row, status = site(dict(mandatory_regions=[0], normalized="لا", bbox=[10, 10, 30, 30]), [])
        self.assertIsNone(row)
        self.assertEqual(status, "small_support_box")


if __name__ == "__main__":
    unittest.main()
