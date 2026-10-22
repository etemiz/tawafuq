"""Independent finite ground truths for the historical pilot's envelopes."""

from itertools import product
import unittest

from historical_copy_analysis import bounds
from historical_copy_pilot import surfaces


class HistoricalCopyTests(unittest.TestCase):
    def test_exhaustive_coordinate_envelopes(self):
        rows = [dict(t=i, page=1, row=i, center=x, frame_width=100, word="الله")
                for i, x in enumerate((10, 13, 18))]
        report = bounds(rows, 0.05, center_error=2, frame_edge_error=1)
        guaranteed = set(report["guaranteed_token_ids"])
        possible = set(report["possible_token_ids"])
        for centers in product(*(range(r["center"]-2, r["center"]+3) for r in rows)):
            for width in range(98, 103):
                actual = {i for i in range(3) if any(i != j and
                          20*abs(centers[i]-centers[j]) <= width for j in range(3))}
                self.assertTrue(guaranteed <= actual <= possible)

    def test_exact_threshold_and_endpoints_once(self):
        rows = [dict(t=i, page=1, row=i, center=x, frame_width=1000, word="الله")
                for i, x in enumerate((100, 115, 130))]
        report = bounds(rows, 0.015)
        self.assertEqual(report["midpoint_aligned"], 3)
        self.assertEqual(len(report["possible_pairs"]), 2)
        self.assertEqual(report["guaranteed_aligned"], report["possibly_aligned"])

    def test_page_row_and_spelling_exclusions(self):
        rows = [dict(t=1, page=1, row=1, center=10, frame_width=100, word="الله"),
                dict(t=2, page=1, row=1, center=10, frame_width=100, word="الله"),
                dict(t=3, page=2, row=2, center=10, frame_width=100, word="الله"),
                dict(t=4, page=1, row=2, center=10, frame_width=100, word="بالله")]
        self.assertEqual(bounds(rows, 0.02)["midpoint_token_ids"], [1, 2, 4])
        self.assertEqual(bounds(rows, 0.02, standalone=True)["midpoint_aligned"], 0)

    def test_tei_uses_actual_labels_and_relative_data_paths(self):
        xml = b'''<TEI xmlns="http://www.tei-c.org/ns/1.0"><facsimile>
          <surface n="50r"><graphic url="master/9372_0105.tif"/>
          <graphic width="100px" height="200px" url="web/9372_0105_web.jpg"/></surface>
          <surface n="Insert"><graphic url="web/9372_0106_web.jpg"/></surface>
          <surface n="50v"><graphic url="web/9372_0107_web.jpg"/></surface>
        </facsimile></TEI>'''
        result = surfaces(xml)
        self.assertTrue(result["50r"]["url"].endswith("/data/web/9372_0105_web.jpg"))
        self.assertTrue(result["50v"]["url"].endswith("0107_web.jpg"))
        self.assertEqual(result["50r"]["width"], "100px")

    def test_tei_rejects_duplicate_surface_identity(self):
        xml = b'''<TEI xmlns="http://www.tei-c.org/ns/1.0"><facsimile>
          <surface n="50r"><graphic url="web/a_web.jpg"/></surface>
          <surface n="50r"><graphic url="web/b_web.jpg"/></surface>
        </facsimile></TEI>'''
        with self.assertRaises(ValueError):
            surfaces(xml)


if __name__ == "__main__":
    unittest.main()
